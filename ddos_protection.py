"""
Protection DDoS et rate limiting avancé pour NinjaLead.ai
Implémente des mécanismes de protection contre les attaques par déni de service
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from functools import wraps
from flask import request, abort, jsonify, g
import ipaddress
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DDoSProtection:
    """Système de protection DDoS avancé"""
    
    def __init__(self, redis_client=None):
        """
        Initialise le système de protection DDoS
        
        Args:
            redis_client: Client Redis pour le stockage distribué
        """
        self.redis_client = redis_client
        self.request_counts = defaultdict(lambda: deque())
        self.blocked_ips = {}
        self.trusted_ips = set()
        self.load_trusted_ips()
        
        # Configuration par défaut
        self.config = {
            'max_requests_per_minute': 60,
            'max_requests_per_hour': 1000,
            'burst_threshold': 10,  # Requêtes par seconde
            'burst_window': 5,      # Fenêtre en secondes
            'block_duration': 3600, # Durée de blocage en secondes
            'escalation_factor': 2, # Facteur d'escalade pour récidives
            'whitelist_enabled': True,
            'suspicious_patterns': [
                'admin', 'wp-admin', '.env', 'config',
                'phpmyadmin', 'xmlrpc.php', 'wp-login'
            ]
        }
    
    def load_trusted_ips(self):
        """Charge la liste des IPs de confiance"""
        trusted_ranges = [
            '127.0.0.1/32',      # Localhost
            '10.0.0.0/8',        # Réseau privé
            '172.16.0.0/12',     # Réseau privé
            '192.168.0.0/16',    # Réseau privé
        ]
        
        for ip_range in trusted_ranges:
            try:
                network = ipaddress.ip_network(ip_range)
                self.trusted_ips.add(network)
            except ValueError as e:
                logger.warning(f"IP range invalide {ip_range}: {e}")
    
    def is_trusted_ip(self, ip: str) -> bool:
        """Vérifie si une IP est de confiance"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return any(ip_obj in network for network in self.trusted_ips)
        except ValueError:
            return False
    
    def get_client_ip(self) -> str:
        """Récupère l'IP réelle du client"""
        # Gestion des proxies et load balancers
        forwarded_ips = request.headers.get('X-Forwarded-For', '')
        if forwarded_ips:
            # Prend la première IP (client original)
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or '127.0.0.1'
    
    def analyze_request_pattern(self, ip: str, path: str, user_agent: str) -> Dict[str, any]:
        """Analyse les patterns de requête pour détecter les comportements suspects"""
        suspicion_score = 0
        flags = []
        
        # Vérification des patterns suspects dans l'URL
        for pattern in self.config['suspicious_patterns']:
            if pattern.lower() in path.lower():
                suspicion_score += 10
                flags.append(f"suspicious_path:{pattern}")
        
        # Analyse de l'User-Agent
        if not user_agent or len(user_agent) < 10:
            suspicion_score += 5
            flags.append("suspicious_user_agent")
        
        # Vérification des bots connus
        bot_indicators = ['bot', 'crawler', 'spider', 'scraper']
        if any(indicator in user_agent.lower() for indicator in bot_indicators):
            suspicion_score += 3
            flags.append("bot_detected")
        
        # Analyse de la fréquence
        current_time = time.time()
        if ip in self.request_counts:
            recent_requests = [t for t in self.request_counts[ip] if current_time - t < 60]
            if len(recent_requests) > self.config['max_requests_per_minute']:
                suspicion_score += 15
                flags.append("high_frequency")
        
        return {
            'suspicion_score': suspicion_score,
            'flags': flags,
            'is_suspicious': suspicion_score > 10
        }
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, Dict[str, any]]:
        """Vérifie les limites de taux pour une IP"""
        current_time = time.time()
        
        # Nettoie les anciennes entrées
        if ip in self.request_counts:
            self.request_counts[ip] = deque([
                t for t in self.request_counts[ip] 
                if current_time - t < 3600  # Garde 1 heure d'historique
            ])
        
        # Ajoute la requête actuelle
        self.request_counts[ip].append(current_time)
        
        # Vérifications des limites
        recent_minute = [t for t in self.request_counts[ip] if current_time - t < 60]
        recent_hour = [t for t in self.request_counts[ip] if current_time - t < 3600]
        recent_burst = [t for t in self.request_counts[ip] if current_time - t < self.config['burst_window']]
        
        limits_exceeded = []
        
        if len(recent_minute) > self.config['max_requests_per_minute']:
            limits_exceeded.append('minute_limit')
        
        if len(recent_hour) > self.config['max_requests_per_hour']:
            limits_exceeded.append('hour_limit')
        
        if len(recent_burst) > self.config['burst_threshold']:
            limits_exceeded.append('burst_limit')
        
        return len(limits_exceeded) == 0, {
            'requests_last_minute': len(recent_minute),
            'requests_last_hour': len(recent_hour),
            'requests_last_burst': len(recent_burst),
            'limits_exceeded': limits_exceeded
        }
    
    def block_ip(self, ip: str, duration: int = None, reason: str = "Rate limit exceeded"):
        """Bloque une IP pour une durée donnée"""
        if self.is_trusted_ip(ip):
            logger.warning(f"Tentative de blocage d'une IP de confiance: {ip}")
            return
        
        block_duration = duration or self.config['block_duration']
        
        # Escalade pour les récidives
        if ip in self.blocked_ips:
            block_duration *= self.config['escalation_factor']
            reason += " (escalation)"
        
        self.blocked_ips[ip] = {
            'blocked_at': time.time(),
            'duration': block_duration,
            'reason': reason,
            'escalation_level': self.blocked_ips.get(ip, {}).get('escalation_level', 0) + 1
        }
        
        logger.warning(f"IP bloquée: {ip} pour {block_duration}s - Raison: {reason}")
        
        # Stockage en Redis si disponible
        if self.redis_client:
            try:
                key = f"blocked_ip:{ip}"
                self.redis_client.setex(key, block_duration, reason)
            except Exception as e:
                logger.error(f"Erreur lors du stockage Redis du blocage: {e}")
    
    def is_ip_blocked(self, ip: str) -> Tuple[bool, Optional[str]]:
        """Vérifie si une IP est bloquée"""
        current_time = time.time()
        
        # Vérification locale
        if ip in self.blocked_ips:
            block_info = self.blocked_ips[ip]
            if current_time - block_info['blocked_at'] < block_info['duration']:
                return True, block_info['reason']
            else:
                # Le blocage a expiré
                del self.blocked_ips[ip]
        
        # Vérification Redis si disponible
        if self.redis_client:
            try:
                key = f"blocked_ip:{ip}"
                reason = self.redis_client.get(key)
                if reason:
                    return True, reason
            except Exception as e:
                logger.error(f"Erreur lors de la vérification Redis: {e}")
        
        return False, None
    
    def process_request(self, ip: str = None) -> Tuple[bool, Dict[str, any]]:
        """Traite une requête et détermine si elle doit être autorisée"""
        ip = ip or self.get_client_ip()
        
        # Vérification du blocage existant
        is_blocked, block_reason = self.is_ip_blocked(ip)
        if is_blocked:
            return False, {
                'action': 'blocked',
                'reason': block_reason,
                'ip': ip
            }
        
        # IPs de confiance passent sans vérification
        if self.is_trusted_ip(ip):
            return True, {
                'action': 'allowed',
                'reason': 'trusted_ip',
                'ip': ip
            }
        
        # Vérification des limites de taux
        rate_ok, rate_info = self.check_rate_limit(ip)
        
        # Analyse des patterns suspects
        pattern_analysis = self.analyze_request_pattern(
            ip, 
            request.path, 
            request.headers.get('User-Agent', '')
        )
        
        # Décision finale
        if not rate_ok:
            self.block_ip(ip, reason=f"Rate limit: {', '.join(rate_info['limits_exceeded'])}")
            return False, {
                'action': 'blocked',
                'reason': 'rate_limit_exceeded',
                'details': rate_info,
                'ip': ip
            }
        
        if pattern_analysis['is_suspicious']:
            if pattern_analysis['suspicion_score'] > 20:
                self.block_ip(ip, reason=f"Suspicious activity: {', '.join(pattern_analysis['flags'])}")
                return False, {
                    'action': 'blocked',
                    'reason': 'suspicious_activity',
                    'details': pattern_analysis,
                    'ip': ip
                }
            else:
                # Activité suspecte mais pas critique - log seulement
                logger.warning(f"Activité suspecte détectée pour {ip}: {pattern_analysis['flags']}")
        
        return True, {
            'action': 'allowed',
            'rate_info': rate_info,
            'pattern_analysis': pattern_analysis,
            'ip': ip
        }
    
    def get_protection_stats(self) -> Dict[str, any]:
        """Récupère les statistiques de protection"""
        current_time = time.time()
        
        # Nettoie les IPs bloquées expirées
        expired_blocks = []
        for ip, block_info in self.blocked_ips.items():
            if current_time - block_info['blocked_at'] >= block_info['duration']:
                expired_blocks.append(ip)
        
        for ip in expired_blocks:
            del self.blocked_ips[ip]
        
        return {
            'currently_blocked_ips': len(self.blocked_ips),
            'total_tracked_ips': len(self.request_counts),
            'trusted_networks': len(self.trusted_ips),
            'config': self.config,
            'blocked_ips_details': {
                ip: {
                    'reason': info['reason'],
                    'blocked_since': datetime.fromtimestamp(info['blocked_at']).isoformat(),
                    'expires_at': datetime.fromtimestamp(info['blocked_at'] + info['duration']).isoformat(),
                    'escalation_level': info['escalation_level']
                }
                for ip, info in self.blocked_ips.items()
            }
        }

# Instance globale de protection DDoS
ddos_protection = DDoSProtection()

def ddos_protection_middleware():
    """Middleware Flask pour la protection DDoS"""
    # Skip pour les routes d'administration et de santé
    skip_paths = ['/health', '/metrics', '/admin/ddos-stats']
    if request.path in skip_paths:
        return
    
    allowed, details = ddos_protection.process_request()
    
    if not allowed:
        # Log de l'incident de sécurité
        logger.warning(f"Requête bloquée par protection DDoS: {details}")
        
        # Retourne une réponse d'erreur appropriée
        if request.is_json:
            response = jsonify({
                'error': 'Too Many Requests',
                'message': 'Your request has been blocked due to suspicious activity',
                'code': 'RATE_LIMITED'
            })
            response.status_code = 429
        else:
            abort(429)  # Too Many Requests
        
        return response

def require_ddos_check(f):
    """Décorateur pour forcer la vérification DDoS sur une route spécifique"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        allowed, details = ddos_protection.process_request()
        if not allowed:
            if request.is_json:
                return jsonify({
                    'error': 'Access Denied',
                    'reason': details.get('reason'),
                    'details': details
                }), 429
            else:
                abort(429)
        
        # Ajoute les infos de protection au contexte
        g.ddos_check = details
        return f(*args, **kwargs)
    
    return decorated_function

def get_ddos_stats():
    """Fonction utilitaire pour obtenir les statistiques DDoS"""
    return ddos_protection.get_protection_stats()

def whitelist_ip(ip: str):
    """Ajoute une IP à la liste blanche"""
    try:
        network = ipaddress.ip_network(f"{ip}/32")
        ddos_protection.trusted_ips.add(network)
        logger.info(f"IP ajoutée à la liste blanche: {ip}")
        return True
    except ValueError as e:
        logger.error(f"IP invalide pour la liste blanche {ip}: {e}")
        return False

def unblock_ip(ip: str):
    """Débloque manuellement une IP"""
    if ip in ddos_protection.blocked_ips:
        del ddos_protection.blocked_ips[ip]
        logger.info(f"IP débloquée manuellement: {ip}")
        
        # Supprime aussi de Redis
        if ddos_protection.redis_client:
            try:
                key = f"blocked_ip:{ip}"
                ddos_protection.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Erreur lors de la suppression Redis: {e}")
        
        return True
    return False

if __name__ == "__main__":
    # Test du système de protection DDoS
    print("Test du système de protection DDoS...")
    
    stats = get_ddos_stats()
    print(f"IPs bloquées: {stats['currently_blocked_ips']}")
    print(f"IPs trackées: {stats['total_tracked_ips']}")
    print(f"Réseaux de confiance: {stats['trusted_networks']}")
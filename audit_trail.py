"""
Système d'audit trail pour les actions sensibles dans NinjaLead.ai
Traçabilité complète des actions critiques avec horodatage et contexte
"""

import json
import datetime
from enum import Enum
from typing import Dict, Any, Optional
from flask import request, g
from flask_login import current_user
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from models import db

class AuditAction(Enum):
    """Types d'actions auditables"""
    # Authentification
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"
    USER_REGISTER = "user_register"
    
    # Gestion des données
    CAMPAIGN_CREATE = "campaign_create"
    CAMPAIGN_UPDATE = "campaign_update"
    CAMPAIGN_DELETE = "campaign_delete"
    
    CUSTOMER_CREATE = "customer_create"
    CUSTOMER_UPDATE = "customer_update"
    CUSTOMER_DELETE = "customer_delete"
    
    PRODUCT_CREATE = "product_create"
    PRODUCT_UPDATE = "product_update"
    PRODUCT_DELETE = "product_delete"
    
    # Actions IA
    AI_GENERATION = "ai_generation"
    AI_IMAGE_GENERATION = "ai_image_generation"
    
    # Sécurité
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Administration
    USER_ROLE_CHANGE = "user_role_change"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    
    # Import/Export
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"

class AuditSeverity(Enum):
    """Niveaux de gravité pour l'audit"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditLog(db.Model):
    """Modèle pour les logs d'audit"""
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    
    # Informations temporelles
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Action auditée
    action = Column(String(50), nullable=False)
    severity = Column(String(20), default=AuditSeverity.MEDIUM.value, nullable=False)
    
    # Utilisateur et session
    user_id = Column(Integer, nullable=True)  # Null pour les actions anonymes
    username = Column(String(64), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Informations de contexte
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(100), nullable=True)
    http_method = Column(String(10), nullable=True)
    
    # Détails de l'action
    resource_type = Column(String(50), nullable=True)  # Type de ressource affectée
    resource_id = Column(String(50), nullable=True)    # ID de la ressource
    old_values = Column(JSONB, nullable=True)          # Valeurs avant modification
    new_values = Column(JSONB, nullable=True)          # Valeurs après modification
    
    # Message descriptif
    description = Column(Text, nullable=False)
    
    # Données additionnelles
    metadata = Column(JSONB, nullable=True)
    
    # Indicateurs
    success = Column(Boolean, default=True, nullable=False)
    requires_attention = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.username} at {self.timestamp}>'
    
    def to_dict(self):
        """Convertit l'entrée d'audit en dictionnaire"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'action': self.action,
            'severity': self.severity,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'endpoint': self.endpoint,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'description': self.description,
            'success': self.success,
            'requires_attention': self.requires_attention,
            'metadata': self.metadata
        }

class AuditTrail:
    """Gestionnaire du système d'audit trail"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le système d'audit avec l'application Flask"""
        app.config.setdefault('AUDIT_ENABLED', True)
        app.config.setdefault('AUDIT_RETENTION_DAYS', 365)  # 1 an de rétention
        app.config.setdefault('AUDIT_ANONYMIZE_AFTER_DAYS', 90)  # Anonymisation après 90 jours
        
        # Créer les tables si nécessaire
        with app.app_context():
            db.create_all()
    
    def log_action(self, 
                   action: AuditAction,
                   description: str,
                   severity: AuditSeverity = AuditSeverity.MEDIUM,
                   resource_type: Optional[str] = None,
                   resource_id: Optional[str] = None,
                   old_values: Optional[Dict[str, Any]] = None,
                   new_values: Optional[Dict[str, Any]] = None,
                   success: bool = True,
                   requires_attention: bool = False,
                   metadata: Optional[Dict[str, Any]] = None):
        """
        Enregistre une action dans l'audit trail
        
        Args:
            action: Type d'action auditée
            description: Description de l'action
            severity: Niveau de gravité
            resource_type: Type de ressource affectée
            resource_id: ID de la ressource
            old_values: Valeurs avant modification
            new_values: Valeurs après modification
            success: Indique si l'action a réussi
            requires_attention: Indique si l'action nécessite une attention
            metadata: Données additionnelles
        """
        
        if not self.app.config.get('AUDIT_ENABLED', True):
            return
        
        try:
            # Collecter les informations de contexte
            user_id = None
            username = None
            session_id = None
            ip_address = None
            user_agent = None
            endpoint = None
            http_method = None
            
            # Informations utilisateur
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
                username = current_user.username
            
            # Informations de requête
            if request:
                session_id = getattr(g, 'request_id', None) or request.headers.get('X-Request-ID')
                ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                user_agent = request.headers.get('User-Agent')
                endpoint = request.endpoint
                http_method = request.method
            
            # Filtrer les données sensibles
            filtered_old_values = self._filter_sensitive_data(old_values) if old_values else None
            filtered_new_values = self._filter_sensitive_data(new_values) if new_values else None
            
            # Créer l'entrée d'audit
            audit_entry = AuditLog(
                action=action.value,
                severity=severity.value,
                user_id=user_id,
                username=username,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                http_method=http_method,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                old_values=filtered_old_values,
                new_values=filtered_new_values,
                description=description,
                success=success,
                requires_attention=requires_attention,
                metadata=metadata
            )
            
            db.session.add(audit_entry)
            db.session.commit()
            
            # Log critique pour les actions à haute gravité
            if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                self._log_critical_action(audit_entry)
                
        except Exception as e:
            # Ne pas faire échouer l'action principale à cause de l'audit
            print(f"Erreur lors de l'enregistrement de l'audit: {e}")
            try:
                db.session.rollback()
            except:
                pass
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filtre les données sensibles des logs d'audit"""
        if not isinstance(data, dict):
            return data
        
        sensitive_fields = {
            'password', 'password_hash', 'secret', 'token', 'api_key',
            'credit_card', 'ssn', 'social_security', 'bank_account'
        }
        
        filtered_data = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                filtered_data[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered_data[key] = self._filter_sensitive_data(value)
            else:
                filtered_data[key] = value
        
        return filtered_data
    
    def _log_critical_action(self, audit_entry: AuditLog):
        """Log spécial pour les actions critiques"""
        from centralized_logging import centralized_logger
        
        if hasattr(centralized_logger, 'log_security'):
            centralized_logger.log_security(
                'CRITICAL' if audit_entry.severity == AuditSeverity.CRITICAL.value else 'WARNING',
                f"Critical audit action: {audit_entry.action}",
                {
                    'audit_id': audit_entry.id,
                    'user_id': audit_entry.user_id,
                    'ip_address': audit_entry.ip_address,
                    'action': audit_entry.action,
                    'description': audit_entry.description,
                    'requires_attention': audit_entry.requires_attention
                }
            )
    
    def get_user_audit_trail(self, user_id: int, limit: int = 100) -> list:
        """Récupère l'historique d'audit pour un utilisateur"""
        return AuditLog.query.filter_by(user_id=user_id)\
                           .order_by(AuditLog.timestamp.desc())\
                           .limit(limit)\
                           .all()
    
    def get_resource_audit_trail(self, resource_type: str, resource_id: str, limit: int = 50) -> list:
        """Récupère l'historique d'audit pour une ressource"""
        return AuditLog.query.filter_by(resource_type=resource_type, resource_id=resource_id)\
                           .order_by(AuditLog.timestamp.desc())\
                           .limit(limit)\
                           .all()
    
    def get_security_events(self, hours: int = 24, limit: int = 100) -> list:
        """Récupère les événements de sécurité récents"""
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        
        return AuditLog.query.filter(
            AuditLog.timestamp >= since,
            AuditLog.action.in_([
                AuditAction.SECURITY_VIOLATION.value,
                AuditAction.RATE_LIMIT_EXCEEDED.value,
                AuditAction.USER_LOGIN_FAILED.value
            ])
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    def get_audit_stats(self, days: int = 7) -> Dict[str, Any]:
        """Génère des statistiques d'audit"""
        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        # Compter les actions par type
        action_counts = db.session.query(
            AuditLog.action,
            db.func.count(AuditLog.id).label('count')
        ).filter(AuditLog.timestamp >= since)\
         .group_by(AuditLog.action)\
         .all()
        
        # Compter les échecs
        failed_actions = AuditLog.query.filter(
            AuditLog.timestamp >= since,
            AuditLog.success == False
        ).count()
        
        # Actions nécessitant une attention
        attention_required = AuditLog.query.filter(
            AuditLog.timestamp >= since,
            AuditLog.requires_attention == True
        ).count()
        
        return {
            'period_days': days,
            'total_actions': sum(count for _, count in action_counts),
            'action_breakdown': dict(action_counts),
            'failed_actions': failed_actions,
            'attention_required': attention_required,
            'top_users': self._get_top_users_stats(since),
            'security_events': len(self.get_security_events(days * 24))
        }
    
    def _get_top_users_stats(self, since: datetime.datetime, limit: int = 10):
        """Statistiques des utilisateurs les plus actifs"""
        return db.session.query(
            AuditLog.username,
            db.func.count(AuditLog.id).label('action_count')
        ).filter(
            AuditLog.timestamp >= since,
            AuditLog.username.isnot(None)
        ).group_by(AuditLog.username)\
         .order_by(db.func.count(AuditLog.id).desc())\
         .limit(limit)\
         .all()

# Instance globale du système d'audit
audit_trail = AuditTrail()

def audit_action(action: AuditAction, description: str, **kwargs):
    """Fonction raccourcie pour enregistrer une action d'audit"""
    audit_trail.log_action(action, description, **kwargs)

def audit_login_success(user):
    """Audit de connexion réussie"""
    audit_action(
        AuditAction.USER_LOGIN,
        f"Utilisateur {user.username} connecté avec succès",
        severity=AuditSeverity.LOW,
        resource_type="user",
        resource_id=user.id
    )

def audit_login_failed(username: str, reason: str = "Invalid credentials"):
    """Audit de tentative de connexion échouée"""
    audit_action(
        AuditAction.USER_LOGIN_FAILED,
        f"Échec de connexion pour {username}: {reason}",
        severity=AuditSeverity.MEDIUM,
        success=False,
        requires_attention=True,
        metadata={"failure_reason": reason}
    )

def audit_security_violation(violation_type: str, details: str):
    """Audit de violation de sécurité"""
    audit_action(
        AuditAction.SECURITY_VIOLATION,
        f"Violation de sécurité détectée: {violation_type}",
        severity=AuditSeverity.HIGH,
        success=False,
        requires_attention=True,
        metadata={"violation_type": violation_type, "details": details}
    )

def audit_data_change(action: AuditAction, resource_type: str, resource_id: str, 
                     old_data: Dict, new_data: Dict, description: str):
    """Audit de modification de données"""
    audit_action(
        action,
        description,
        severity=AuditSeverity.MEDIUM,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_data,
        new_values=new_data
    )
"""
Module de vérification de l'état de santé de l'application
Fournit des endpoints pour monitoring et diagnostics
"""

import os
import json
import time
import psutil
from datetime import datetime, timedelta
from flask import jsonify, request
from sqlalchemy import text
# Imports will be done dynamically to avoid circular imports
import redis

class HealthChecker:
    """Classe pour gérer les vérifications de santé de l'application"""
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialise la connexion Redis si disponible"""
        try:
            redis_url = os.environ.get("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
                # Test de connexion
                self.redis_client.ping()
                app.logger.info("Redis connection established")
            else:
                app.logger.warning("REDIS_URL not configured")
        except Exception as e:
            app.logger.error(f"Redis connection failed: {str(e)}")
            self.redis_client = None

    def check_database(self):
        """Vérifie la connectivité de la base de données"""
        try:
            start_time = time.time()
            result = db.session.execute(text("SELECT 1")).fetchone()
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy" if result else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def check_redis(self):
        """Vérifie la connectivité Redis"""
        if not self.redis_client:
            return {
                "status": "not_configured",
                "message": "Redis not configured",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            start_time = time.time()
            self.redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def check_system_resources(self):
        """Vérifie les ressources système"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": round((disk.used / disk.total) * 100, 2)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def check_ai_services(self):
        """Vérifie la disponibilité des services IA"""
        openai_configured = bool(os.environ.get("OPENAI_API_KEY"))
        xai_configured = bool(os.environ.get("XAI_API_KEY"))
        
        return {
            "status": "configured" if (openai_configured or xai_configured) else "not_configured",
            "openai": "configured" if openai_configured else "not_configured",
            "xai": "configured" if xai_configured else "not_configured",
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_application_info(self):
        """Retourne les informations générales de l'application"""
        return {
            "name": "NinjaLead.ai",
            "version": os.environ.get("APP_VERSION", "1.0.0"),
            "environment": os.environ.get("ENVIRONMENT", "production"),
            "uptime_seconds": time.time() - psutil.boot_time(),
            "python_version": f"{psutil.version_info.major}.{psutil.version_info.minor}",
            "timestamp": datetime.utcnow().isoformat()
        }

# Instance globale du checker
health_checker = HealthChecker()

def register_health_routes(app):
    """Enregistre les routes de health check"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Endpoint principal de vérification de santé"""
        db_status = health_checker.check_database()
        redis_status = health_checker.check_redis()
        system_status = health_checker.check_system_resources()
        ai_status = health_checker.check_ai_services()
        app_info = health_checker.get_application_info()
        
        # Détermine le statut global
        overall_status = "healthy"
        if db_status["status"] != "healthy":
            overall_status = "unhealthy"
        elif system_status["status"] != "healthy":
            overall_status = "degraded"
        elif redis_status["status"] == "unhealthy":
            overall_status = "degraded"
        
        response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "application": app_info,
            "services": {
                "database": db_status,
                "redis": redis_status,
                "ai_services": ai_status
            },
            "system": system_status
        }
        
        # Code de statut HTTP basé sur l'état
        status_code = 200 if overall_status == "healthy" else 503
        
        return jsonify(response), status_code

    @app.route('/health/live', methods=['GET'])
    def liveness_check():
        """Endpoint simple pour vérifier si l'application est vivante"""
        return jsonify({
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    @app.route('/health/ready', methods=['GET'])
    def readiness_check():
        """Endpoint pour vérifier si l'application est prête à servir du trafic"""
        db_status = health_checker.check_database()
        
        if db_status["status"] == "healthy":
            return jsonify({
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "not_ready",
                "reason": "Database not available",
                "timestamp": datetime.utcnow().isoformat()
            }), 503

    @app.route('/health/detailed', methods=['GET'])
    def detailed_health():
        """Endpoint détaillé pour le monitoring avancé"""
        # Vérifications détaillées
        checks = {
            "database": health_checker.check_database(),
            "redis": health_checker.check_redis(),
            "system": health_checker.check_system_resources(),
            "ai_services": health_checker.check_ai_services()
        }
        
        # Métriques supplémentaires
        try:
            from models import User, Boutique, Campaign
            user_count = db.session.query(User).count()
            boutique_count = db.session.query(Boutique).count()
            campaign_count = db.session.query(Campaign).count()
            
            metrics = {
                "users_total": user_count,
                "boutiques_total": boutique_count,
                "campaigns_total": campaign_count
            }
        except Exception as e:
            metrics = {"error": f"Unable to fetch metrics: {str(e)}"}
        
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "application": health_checker.get_application_info(),
            "checks": checks,
            "metrics": metrics
        }), 200

    @app.route('/metrics', methods=['GET'])
    def prometheus_metrics():
        """Endpoint compatible Prometheus pour les métriques"""
        try:
            system = health_checker.check_system_resources()
            db_status = health_checker.check_database()
            
            metrics = []
            
            # Métriques système
            if system["status"] == "healthy":
                metrics.append(f'system_cpu_percent {system["cpu_percent"]}')
                metrics.append(f'system_memory_percent {system["memory"]["percent"]}')
                metrics.append(f'system_disk_percent {system["disk"]["percent"]}')
            
            # Métriques base de données
            db_healthy = 1 if db_status["status"] == "healthy" else 0
            metrics.append(f'database_healthy {db_healthy}')
            
            if "response_time_ms" in db_status:
                metrics.append(f'database_response_time_ms {db_status["response_time_ms"]}')
            
            # Métriques application
            try:
                from models import User, Boutique, Campaign
                user_count = db.session.query(User).count()
                boutique_count = db.session.query(Boutique).count()
                campaign_count = db.session.query(Campaign).count()
                
                metrics.append(f'app_users_total {user_count}')
                metrics.append(f'app_boutiques_total {boutique_count}')
                metrics.append(f'app_campaigns_total {campaign_count}')
            except Exception:
                pass
            
            return '\n'.join(metrics), 200, {'Content-Type': 'text/plain'}
            
        except Exception as e:
            app.logger.error(f"Error generating metrics: {str(e)}")
            return f"# Error generating metrics: {str(e)}", 500, {'Content-Type': 'text/plain'}
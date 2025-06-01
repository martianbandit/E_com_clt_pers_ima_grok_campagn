"""
Système de logs centralisés avec rotation pour NinjaLead.ai
Gestion avancée des logs avec niveaux, rotation, et agrégation
"""

import logging
import logging.handlers
import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import gzip
import shutil

class JsonFormatter(logging.Formatter):
    """Formateur JSON pour les logs structurés"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Ajouter les données contextuelles
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class SecurityFormatter(logging.Formatter):
    """Formateur spécialisé pour les logs de sécurité"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'event_type': 'security',
            'severity': record.levelname,
            'message': record.getMessage(),
            'source_ip': getattr(record, 'ip_address', 'unknown'),
            'user_agent': getattr(record, 'user_agent', 'unknown'),
            'endpoint': getattr(record, 'endpoint', 'unknown'),
            'attack_type': getattr(record, 'attack_type', 'unknown'),
            'blocked': getattr(record, 'blocked', False),
            'user_id': getattr(record, 'user_id', None)
        }
        
        return json.dumps(log_entry, ensure_ascii=False)

class CentralizedLogger:
    """Gestionnaire centralisé des logs avec rotation et archivage"""
    
    def __init__(self, app=None):
        self.app = app
        self.loggers = {}
        self.log_dir = Path('logs')
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le système de logs avec l'application Flask"""
        # Configuration par défaut
        app.config.setdefault('LOG_LEVEL', 'INFO')
        app.config.setdefault('LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10MB
        app.config.setdefault('LOG_BACKUP_COUNT', 5)
        app.config.setdefault('LOG_RETENTION_DAYS', 30)
        
        # Créer le répertoire de logs
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurer les différents types de logs
        self._setup_application_logger(app)
        self._setup_security_logger(app)
        self._setup_performance_logger(app)
        self._setup_business_logger(app)
        self._setup_error_logger(app)
        
        # Middleware pour les logs de requêtes
        self._setup_request_logging(app)
        
        # Nettoyage automatique des anciens logs
        self._setup_log_cleanup(app)
    
    def _setup_application_logger(self, app):
        """Configure le logger principal de l'application"""
        logger = logging.getLogger('ninjalead.app')
        logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        
        # Handler avec rotation
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'application.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
        # Handler console pour le développement
        if app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(console_handler)
        
        self.loggers['app'] = logger
    
    def _setup_security_logger(self, app):
        """Configure le logger de sécurité"""
        logger = logging.getLogger('ninjalead.security')
        logger.setLevel(logging.WARNING)
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'security.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        handler.setFormatter(SecurityFormatter())
        logger.addHandler(handler)
        
        self.loggers['security'] = logger
    
    def _setup_performance_logger(self, app):
        """Configure le logger de performance"""
        logger = logging.getLogger('ninjalead.performance')
        logger.setLevel(logging.INFO)
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'performance.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
        self.loggers['performance'] = logger
    
    def _setup_business_logger(self, app):
        """Configure le logger pour les métriques business"""
        logger = logging.getLogger('ninjalead.business')
        logger.setLevel(logging.INFO)
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'business.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
        self.loggers['business'] = logger
    
    def _setup_error_logger(self, app):
        """Configure le logger d'erreurs"""
        logger = logging.getLogger('ninjalead.errors')
        logger.setLevel(logging.ERROR)
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'errors.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
        self.loggers['error'] = logger
    
    def _setup_request_logging(self, app):
        """Configure le middleware de logging des requêtes"""
        
        @app.before_request
        def log_request_start():
            from flask import request, g
            import time
            import uuid
            
            g.start_time = time.time()
            g.request_id = str(uuid.uuid4())
            
            # Log de début de requête
            self.log_request('INFO', 'Request started', {
                'request_id': g.request_id,
                'method': request.method,
                'endpoint': request.endpoint,
                'path': request.path,
                'user_agent': request.headers.get('User-Agent'),
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            })
        
        @app.after_request
        def log_request_end(response):
            from flask import g
            import time
            
            duration = time.time() - g.start_time
            
            # Log de fin de requête
            self.log_request('INFO', 'Request completed', {
                'request_id': getattr(g, 'request_id', 'unknown'),
                'status_code': response.status_code,
                'duration': round(duration * 1000, 2)  # en millisecondes
            })
            
            # Log de performance si la requête est lente
            if duration > 1.0:  # Plus d'une seconde
                self.log_performance('WARNING', 'Slow request detected', {
                    'request_id': getattr(g, 'request_id', 'unknown'),
                    'duration': round(duration * 1000, 2),
                    'threshold_exceeded': True
                })
            
            return response
    
    def _setup_log_cleanup(self, app):
        """Configure le nettoyage automatique des anciens logs"""
        retention_days = app.config['LOG_RETENTION_DAYS']
        
        def cleanup_old_logs():
            """Supprime les logs plus anciens que la période de rétention"""
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            for log_file in self.log_dir.glob('*.log.*'):
                try:
                    # Vérifier la date de modification du fichier
                    mtime = datetime.datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        # Comprimer le fichier avant suppression
                        compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Supprimer le fichier original
                        log_file.unlink()
                        
                        self.log_app('INFO', f'Archived and removed old log file: {log_file.name}')
                
                except Exception as e:
                    self.log_error('ERROR', f'Failed to cleanup log file {log_file}: {str(e)}')
        
        # Programmer le nettoyage quotidien (à implémenter avec un scheduler)
        # Pour l'instant, on fait juste le nettoyage au démarrage
        cleanup_old_logs()
    
    def log_app(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log un message de l'application"""
        logger = self.loggers.get('app')
        if logger:
            self._log_with_extra(logger, level, message, extra)
    
    def log_security(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log un événement de sécurité"""
        logger = self.loggers.get('security')
        if logger:
            # Ajouter des informations de contexte de sécurité
            if extra is None:
                extra = {}
            extra['event_type'] = 'security'
            self._log_with_extra(logger, level, message, extra)
    
    def log_performance(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log une métrique de performance"""
        logger = self.loggers.get('performance')
        if logger:
            if extra is None:
                extra = {}
            extra['event_type'] = 'performance'
            self._log_with_extra(logger, level, message, extra)
    
    def log_business(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log une métrique business"""
        logger = self.loggers.get('business')
        if logger:
            if extra is None:
                extra = {}
            extra['event_type'] = 'business'
            self._log_with_extra(logger, level, message, extra)
    
    def log_error(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log une erreur"""
        logger = self.loggers.get('error')
        if logger:
            if extra is None:
                extra = {}
            extra['event_type'] = 'error'
            self._log_with_extra(logger, level, message, extra)
    
    def log_request(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log une requête HTTP"""
        logger = self.loggers.get('app')
        if logger:
            if extra is None:
                extra = {}
            extra['event_type'] = 'request'
            self._log_with_extra(logger, level, message, extra)
    
    def _log_with_extra(self, logger, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Utilitaire pour logger avec des données extra"""
        if extra:
            # Créer un LogRecord avec les données extra
            record = logging.LogRecord(
                name=logger.name,
                level=getattr(logging, level),
                pathname='',
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            
            # Ajouter les données extra
            for key, value in extra.items():
                setattr(record, key, value)
            
            logger.handle(record)
        else:
            getattr(logger, level.lower())(message)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques des logs"""
        stats = {
            'log_directory': str(self.log_dir),
            'log_files': {},
            'total_size': 0
        }
        
        for log_file in self.log_dir.glob('*.log*'):
            try:
                file_stats = log_file.stat()
                stats['log_files'][log_file.name] = {
                    'size': file_stats.st_size,
                    'modified': datetime.datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                }
                stats['total_size'] += file_stats.st_size
            except Exception:
                pass
        
        return stats

# Instance globale du système de logs
centralized_logger = CentralizedLogger()

def setup_logging(app):
    """Fonction d'initialisation du système de logs"""
    centralized_logger.init_app(app)
    return centralized_logger
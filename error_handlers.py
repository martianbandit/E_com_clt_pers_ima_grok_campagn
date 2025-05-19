"""
Module de gestion centralisée des erreurs pour NinjaMark
Implémente des gestionnaires pour différents types d'erreurs
avec des messages utilisateur adaptés.
"""

import logging
import traceback
from flask import render_template, jsonify, request
from sqlalchemy import exc as sqlalchemy_exc

# Logger spécifique pour les erreurs
error_logger = logging.getLogger("ninjamark.errors")

def register_error_handlers(app):
    """
    Enregistre tous les gestionnaires d'erreur pour l'application Flask
    
    Args:
        app: Instance de l'application Flask
    """
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Gestion des erreurs 400 Bad Request"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Bad Request',
                'message': str(error),
                'status_code': 400
            }), 400
        # Redirection vers une page simple pour éviter les boucles infinies
        return render_template('errors/400.html', error=error), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Gestion des erreurs 401 Unauthorized"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentification requise',
                'status_code': 401
            }), 401
        return render_template('errors/401.html', error=error), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Gestion des erreurs 403 Forbidden"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Accès refusé',
                'status_code': 403
            }), 403
        return render_template('errors/403.html', error=error), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Gestion des erreurs 404 Not Found"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Not Found',
                'message': 'La ressource demandée n\'existe pas',
                'status_code': 404
            }), 404
        return render_template('errors/404.html', error=error), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Gestion des erreurs 500 Internal Server Error"""
        # Journalisation détaillée de l'erreur
        error_logger.error(f"Erreur 500: {str(error)}")
        error_logger.error(traceback.format_exc())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Une erreur interne est survenue. L\'équipe technique a été notifiée.',
                'status_code': 500
            }), 500
        return render_template('errors/500.html', error=error), 500
    
    @app.errorhandler(sqlalchemy_exc.SQLAlchemyError)
    def handle_db_error(error):
        """Gestion des erreurs de base de données"""
        error_logger.error(f"Erreur de base de données: {str(error)}")
        error_logger.error(traceback.format_exc())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Database Error',
                'message': 'Une erreur de base de données est survenue. L\'équipe technique a été notifiée.',
                'status_code': 500
            }), 500
        return render_template('errors/db_error.html', error=error), 500
    
    @app.errorhandler(Exception)
    def handle_unhandled_exception(error):
        """Gestionnaire pour toutes les exceptions non gérées"""
        error_logger.error(f"Exception non gérée: {str(error)}")
        error_logger.error(traceback.format_exc())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': 'Unexpected Error',
                'message': 'Une erreur inattendue est survenue. L\'équipe technique a été notifiée.',
                'status_code': 500
            }), 500
        return render_template('errors/generic_error.html', error=error), 500
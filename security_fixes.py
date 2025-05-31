"""
Script pour corriger les vulnérabilités de sécurité détectées
"""

import os
import secrets
from werkzeug.security import generate_password_hash
from flask import request
import re
import html

class SecurityFixes:
    """Classe pour implémenter les corrections de sécurité"""
    
    @staticmethod
    def generate_secure_secret_key():
        """Génère une clé secrète sécurisée"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_input(input_data, input_type="text"):
        """Valide et nettoie les entrées utilisateur"""
        if not input_data:
            return ""
        
        # Nettoyage de base - suppression des caractères dangereux
        if input_type == "email":
            # Validation email basique
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, input_data):
                raise ValueError("Format d'email invalide")
        
        elif input_type == "url":
            # Validation URL basique
            if not input_data.startswith(('http://', 'https://')):
                raise ValueError("URL invalide")
        
        elif input_type == "html":
            # Échappement HTML pour prévenir XSS
            return html.escape(input_data)
        
        # Suppression des caractères de contrôle dangereux
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(input_data))
        
        return cleaned.strip()
    
    @staticmethod
    def sanitize_sql_input(input_data):
        """Nettoie les entrées pour prévenir l'injection SQL"""
        if not input_data:
            return ""
        
        # Suppression des caractères SQL dangereux
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
        cleaned = str(input_data)
        
        for char in dangerous_chars:
            cleaned = cleaned.replace(char, '')
        
        return cleaned.strip()
    
    @staticmethod
    def validate_file_upload(file):
        """Valide les fichiers uploadés"""
        if not file or not file.filename:
            return False, "Aucun fichier sélectionné"
        
        # Extensions autorisées
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.csv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return False, f"Extension de fichier non autorisée: {file_ext}"
        
        # Taille maximale (5MB)
        max_size = 5 * 1024 * 1024
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > max_size:
            return False, "Fichier trop volumineux (max 5MB)"
        
        return True, "Fichier valide"
    
    @staticmethod
    def secure_headers():
        """Retourne les en-têtes de sécurité à ajouter"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'"
        }
    
    @staticmethod
    def rate_limit_check(ip_address, endpoint, max_requests=100, time_window=3600):
        """Vérifie les limites de taux (à implémenter avec Redis ou base de données)"""
        # Cette fonction nécessiterait une implémentation avec Redis ou base de données
        # Pour l'instant, on retourne toujours True
        return True
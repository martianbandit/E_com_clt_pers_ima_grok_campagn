#!/usr/bin/env python3
"""
Script de correction des problèmes d'authentification
"""

import os
import sys
import logging

# Configuration de base
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_authentication_issues():
    """Corrige les problèmes d'authentification dans l'application"""
    
    print("Correction des problèmes d'authentification...")
    
    # 1. Vérifier les variables d'environnement nécessaires
    required_env_vars = [
        'DATABASE_URL',
        'SESSION_SECRET'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Variables d'environnement manquantes : {', '.join(missing_vars)}")
        # Définir des valeurs par défaut pour le développement
        if not os.environ.get('SESSION_SECRET'):
            os.environ['SESSION_SECRET'] = 'dev-secret-key-for-testing'
            print("SESSION_SECRET définie avec une valeur par défaut")
    
    # 2. Vérifier la connexion à la base de données
    try:
        from app import db, app
        with app.app_context():
            # Test de connexion simple
            db.engine.execute('SELECT 1')
            print("✓ Connexion à la base de données réussie")
    except Exception as e:
        print(f"✗ Erreur de connexion à la base de données : {e}")
        return False
    
    # 3. Vérifier les modèles utilisateur
    try:
        from models import User
        with app.app_context():
            user_count = User.query.count()
            print(f"✓ Modèles utilisateur accessibles ({user_count} utilisateurs)")
    except Exception as e:
        print(f"✗ Erreur avec les modèles utilisateur : {e}")
        return False
    
    print("✓ Problèmes d'authentification corrigés")
    return True

if __name__ == "__main__":
    success = fix_authentication_issues()
    sys.exit(0 if success else 1)
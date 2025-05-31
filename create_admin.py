#!/usr/bin/env python3
"""
Script pour créer un compte administrateur
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

def create_admin_user():
    """Crée un compte administrateur"""
    
    # Import des modules Flask
    from app import app, db
    from models import User
    
    with app.app_context():
        # Vérifier si l'admin existe déjà
        admin_email = "admin@markeasy.com"
        existing_admin = User.query.filter_by(email=admin_email).first()
        
        if existing_admin:
            print(f"✓ Compte admin existe déjà : {admin_email}")
            print(f"  Mot de passe : admin123")
            return True
        
        try:
            # Créer un nouvel utilisateur admin
            admin_user = User()
            admin_user.email = admin_email
            admin_user.username = "admin"
            admin_user.first_name = "Admin"
            admin_user.last_name = "MarkEasy"
            admin_user.password_hash = generate_password_hash("admin123")
            admin_user.is_admin = True
            admin_user.is_active = True
            admin_user.email_verified = True
            admin_user.created_at = datetime.utcnow()
            admin_user.updated_at = datetime.utcnow()
            
            # Générer un ID numérique unique
            max_numeric_id = db.session.query(db.func.max(User.numeric_id)).scalar() or 0
            admin_user.numeric_id = max_numeric_id + 1
            
            # Ajouter à la base de données
            db.session.add(admin_user)
            db.session.commit()
            
            print("✓ Compte administrateur créé avec succès !")
            print(f"  Email : {admin_email}")
            print(f"  Mot de passe : admin123")
            print(f"  ID numérique : {admin_user.numeric_id}")
            
            return True
            
        except Exception as e:
            print(f"✗ Erreur lors de la création du compte admin : {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_admin_user()
    if success:
        print("\n🔐 Vous pouvez maintenant vous connecter avec :")
        print("   Email : admin@markeasy.com")
        print("   Mot de passe : admin123")
    sys.exit(0 if success else 1)
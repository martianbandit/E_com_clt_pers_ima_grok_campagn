"""
Script pour mettre à jour le modèle User avec les nouveaux champs
"""
import os
import sqlalchemy as sa
from sqlalchemy import text
from app import app, db

# Liste des colonnes à ajouter
columns_to_add = [
    "username VARCHAR(50) UNIQUE",
    "password_hash VARCHAR(255)",
    "role VARCHAR(20) NOT NULL DEFAULT 'user'",
    "language_preference VARCHAR(10) NOT NULL DEFAULT 'fr'",
    "theme_preference VARCHAR(10) NOT NULL DEFAULT 'dark'",
    "job_title VARCHAR(100)",
    "company VARCHAR(100)",
    "phone VARCHAR(20)",
    "bio TEXT",
    "address TEXT",
    "notification_preferences JSONB DEFAULT '{\"email\": true, \"webapp\": true, \"marketing\": false}'",
    "last_login_at TIMESTAMP",
    "login_count INTEGER DEFAULT 0",
    "active BOOLEAN DEFAULT TRUE"
]

def migrate_users_table():
    """Ajoute les nouvelles colonnes à la table users"""
    print("Début de la migration de la table users...")
    
    with app.app_context():
        connection = db.engine.connect()
        
        # Vérification que la table users existe
        tables = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname=:schema").bindparams(schema='public')).fetchall()
        if 'users' not in [table[0] for table in tables]:
            print("La table users n'existe pas encore, pas besoin de migration.")
            return
        
        # Récupération des colonnes existantes
        columns = connection.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name=:table_name"
        ).bindparams(table_name='users')).fetchall()
        existing_columns = [col[0] for col in columns]
        
        # Ajout des colonnes manquantes
        for column_def in columns_to_add:
            column_name = column_def.split()[0].lower()
            if column_name not in existing_columns:
                try:
                    print(f"Ajout de la colonne {column_name}...")
                    connection.execute(text("ALTER TABLE users ADD COLUMN :column_def").bindparams(column_def=column_def))
                    connection.commit()
                except Exception as e:
                    print(f"Erreur lors de l'ajout de la colonne {column_name}: {e}")
                    connection.rollback()
        
        # Mise à jour de l'utilisateur admin
        try:
            print("Mise à jour de l'utilisateur admin...")
            admin_pwd_hash = 'pbkdf2:sha256:600000$PQEUzntgBhsKNQUX$d7a8180a41e0f6c4a92e58e43d383c5c6aac23e25aadaeaa6a8b7bcb62262d08'
            connection.execute(text("""
                UPDATE users 
                SET username = :username, 
                    role = :role, 
                    password_hash = :password_hash
                WHERE id = :id
            """).bindparams(
                username='admin',
                role='admin',
                password_hash=admin_pwd_hash,
                id='admin'
            ))
            connection.commit()
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'utilisateur admin: {e}")
            connection.rollback()
        
        # Création de la table user_activities si elle n'existe pas
        try:
            print("Création de la table user_activities...")
            # Cette requête ne contient pas de paramètres dynamiques, mais utiliser text() est plus sûr que des chaînes brutes
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user_activities (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    activity_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    ip_address VARCHAR(50),
                    user_agent VARCHAR(255),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.commit()
        except Exception as e:
            print(f"Erreur lors de la création de la table user_activities: {e}")
            connection.rollback()
        
        print("Migration terminée avec succès!")

if __name__ == "__main__":
    migrate_users_table()
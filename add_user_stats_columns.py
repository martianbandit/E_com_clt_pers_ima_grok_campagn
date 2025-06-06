from app import app, db
from sqlalchemy import text

# Script pour ajouter les colonnes de statistiques utilisateur à la table users
with app.app_context():
    try:
        # Vérifier si les colonnes existent déjà
        columns_to_add = {
            'last_login': 'TIMESTAMP',
            'login_count': 'INTEGER',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        for col_name, col_type in columns_to_add.items():
            # Vérifier si la colonne existe - Utiliser des paramètres liés pour éviter l'injection SQL
            check_query = text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='users' AND column_name=:col_name
            """)
            result = db.session.execute(check_query, {"col_name": col_name}).fetchone()
            
            if not result:
                print(f"La colonne {col_name} n'existe pas. Création en cours...")
                
                # Ajouter la colonne - Utiliser des paramètres liés pour éviter l'injection SQL
                if col_name == 'login_count':
                    alter_query = text("""
                    ALTER TABLE users ADD COLUMN :col_name :col_type DEFAULT 0
                    """).bindparams(col_name=col_name, col_type=col_type)
                elif col_name in ['created_at', 'updated_at']:
                    alter_query = text("""
                    ALTER TABLE users ADD COLUMN :col_name :col_type DEFAULT CURRENT_TIMESTAMP
                    """).bindparams(col_name=col_name, col_type=col_type)
                else:
                    alter_query = text("""
                    ALTER TABLE users ADD COLUMN :col_name :col_type
                    """).bindparams(col_name=col_name, col_type=col_type)
                    
                db.session.execute(alter_query)
                db.session.commit()
                print(f"Colonne {col_name} ajoutée avec succès.")
            else:
                print(f"La colonne {col_name} existe déjà.")
        
        print("Migration des colonnes utilisateur terminée avec succès.")
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la migration: {str(e)}")
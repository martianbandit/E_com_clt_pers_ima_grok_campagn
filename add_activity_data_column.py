from app import app, db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text

# Script pour ajouter la colonne activity_data à la table user_activities
with app.app_context():
    try:
        # Vérifier si la colonne existe déjà
        check_query = text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='user_activities' AND column_name='activity_data'
        """)
        result = db.session.execute(check_query).fetchone()
        
        if not result:
            print("La colonne activity_data n'existe pas. Création en cours...")
            alter_query = text("""
            ALTER TABLE user_activities ADD COLUMN activity_data JSONB
            """)
            db.session.execute(alter_query)
            db.session.commit()
            print("Colonne activity_data ajoutée avec succès.")
        else:
            print("La colonne activity_data existe déjà.")
        
        # Vérifier si la colonne metadata existe et la supprimer si nécessaire
        check_query = text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='user_activities' AND column_name='metadata'
        """)
        result = db.session.execute(check_query).fetchone()
        
        if result:
            print("La colonne metadata existe. Suppression en cours...")
            
            # Copier les données de metadata vers activity_data si ce n'est pas déjà fait
            copy_query = text("""
            UPDATE user_activities 
            SET activity_data = metadata 
            WHERE activity_data IS NULL AND metadata IS NOT NULL
            """)
            db.session.execute(copy_query)
            
            # Supprimer la colonne metadata
            alter_query = text("""
            ALTER TABLE user_activities DROP COLUMN metadata
            """)
            db.session.execute(alter_query)
            db.session.commit()
            print("Colonne metadata supprimée avec succès après migration des données.")
        else:
            print("La colonne metadata n'existe pas.")
            
        print("Migration terminée avec succès.")
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la migration: {str(e)}")
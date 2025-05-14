"""
Script pour vérifier la structure de la base de données
"""
from app import app, db
from models import User

def check_database():
    """Vérifie la structure de la base de données"""
    with app.app_context():
        # Vérifier les tables
        print("Tables dans la base de données:")
        tables = [table.name for table in db.metadata.tables.values()]
        print(tables)
        
        # Vérifier les colonnes de la table users
        print("\nColonnes dans la table users:")
        try:
            columns = [column.name for column in db.metadata.tables['users'].columns]
            print(columns)
        except KeyError:
            print("La table 'users' n'existe pas encore.")
            
        # Vérifier si la table user_activities existe
        print("\nTable user_activities existe:", 'user_activities' in tables)
        
        # Vérifier si l'utilisateur admin existe
        print("\nVérification de l'utilisateur admin:")
        admin = User.query.filter_by(id='admin').first()
        if admin:
            print(f"ID: {admin.id}")
            print(f"Email: {admin.email}")
            print(f"Prénom: {admin.first_name}")
            print(f"Nom: {admin.last_name}")
            print(f"Rôle: {getattr(admin, 'role', 'Non défini')}")
            print(f"Préférence de langue: {getattr(admin, 'language_preference', 'Non défini')}")
        else:
            print("L'utilisateur admin n'existe pas.")

if __name__ == "__main__":
    check_database()
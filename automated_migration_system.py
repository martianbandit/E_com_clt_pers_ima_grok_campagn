"""
Système de migrations automatiques pour CI/CD
Gère les migrations de base de données de manière sécurisée et automatisée
"""

import os
import sys
import logging
import hashlib
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class MigrationManager:
    """Gestionnaire des migrations automatiques"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Répertoire des migrations
        self.migrations_dir = Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        
        # Table de suivi des migrations
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Crée la table de suivi des migrations si elle n'existe pas"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(255) UNIQUE NOT NULL,
            file_hash VARCHAR(64) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT,
            rollback_sql TEXT
        );
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
    
    def get_migration_files(self) -> List[Path]:
        """Récupère tous les fichiers de migration triés par nom"""
        migration_files = []
        for file_path in self.migrations_dir.glob("*.py"):
            if file_path.name.startswith("add_") or file_path.name.startswith("migrate_"):
                migration_files.append(file_path)
        
        return sorted(migration_files)
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calcule le hash SHA-256 d'un fichier de migration"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def is_migration_applied(self, migration_name: str, file_hash: str) -> bool:
        """Vérifie si une migration a déjà été appliquée"""
        with self.Session() as session:
            result = session.execute(
                text("SELECT file_hash FROM migration_history WHERE migration_name = :name"),
                {"name": migration_name}
            ).fetchone()
            
            if not result:
                return False
            
            # Vérifier si le hash correspond (détection de modifications)
            return result[0] == file_hash
    
    def apply_migration(self, file_path: Path) -> Dict:
        """Applique une migration et enregistre le résultat"""
        migration_name = file_path.stem
        file_hash = self.calculate_file_hash(file_path)
        
        logger.info(f"Application de la migration: {migration_name}")
        
        try:
            # Importer et exécuter la migration
            spec = __import__(migration_name)
            if hasattr(spec, 'run_migration'):
                success = spec.run_migration()
                
                if success:
                    # Enregistrer le succès
                    with self.Session() as session:
                        session.execute(text("""
                            INSERT INTO migration_history (migration_name, file_hash, success)
                            VALUES (:name, :hash, :success)
                            ON CONFLICT (migration_name) 
                            DO UPDATE SET file_hash = :hash, applied_at = CURRENT_TIMESTAMP, success = :success
                        """), {
                            "name": migration_name,
                            "hash": file_hash,
                            "success": True
                        })
                        session.commit()
                    
                    logger.info(f"Migration {migration_name} appliquée avec succès")
                    return {"success": True, "migration": migration_name}
                else:
                    raise Exception("Migration returned False")
            else:
                raise Exception("No run_migration function found")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erreur lors de l'application de {migration_name}: {error_msg}")
            
            # Enregistrer l'échec
            with self.Session() as session:
                session.execute(text("""
                    INSERT INTO migration_history (migration_name, file_hash, success, error_message)
                    VALUES (:name, :hash, :success, :error)
                    ON CONFLICT (migration_name) 
                    DO UPDATE SET file_hash = :hash, applied_at = CURRENT_TIMESTAMP, 
                                  success = :success, error_message = :error
                """), {
                    "name": migration_name,
                    "hash": file_hash,
                    "success": False,
                    "error": error_msg
                })
                session.commit()
            
            return {"success": False, "migration": migration_name, "error": error_msg}
    
    def run_pending_migrations(self) -> Dict:
        """Exécute toutes les migrations en attente"""
        migration_files = self.get_migration_files()
        results = {
            "applied": [],
            "skipped": [],
            "failed": [],
            "total": len(migration_files)
        }
        
        logger.info(f"Vérification de {len(migration_files)} migrations")
        
        for file_path in migration_files:
            migration_name = file_path.stem
            file_hash = self.calculate_file_hash(file_path)
            
            if self.is_migration_applied(migration_name, file_hash):
                logger.info(f"Migration {migration_name} déjà appliquée - ignorée")
                results["skipped"].append(migration_name)
                continue
            
            # Ajouter le répertoire au path pour l'import
            if str(file_path.parent) not in sys.path:
                sys.path.insert(0, str(file_path.parent))
            
            result = self.apply_migration(file_path)
            
            if result["success"]:
                results["applied"].append(migration_name)
            else:
                results["failed"].append({
                    "migration": migration_name,
                    "error": result.get("error", "Unknown error")
                })
        
        return results
    
    def get_migration_status(self) -> Dict:
        """Retourne le statut des migrations"""
        with self.Session() as session:
            # Migrations appliquées
            applied_result = session.execute(text("""
                SELECT migration_name, applied_at, success, error_message 
                FROM migration_history 
                ORDER BY applied_at DESC
            """)).fetchall()
            
            applied_migrations = []
            for row in applied_result:
                applied_migrations.append({
                    "name": row[0],
                    "applied_at": row[1].isoformat() if row[1] else None,
                    "success": row[2],
                    "error": row[3]
                })
        
        # Migrations disponibles
        available_files = self.get_migration_files()
        available_migrations = [f.stem for f in available_files]
        
        # Migrations en attente
        applied_names = {m["name"] for m in applied_migrations if m["success"]}
        pending_migrations = [name for name in available_migrations if name not in applied_names]
        
        return {
            "applied": applied_migrations,
            "available": available_migrations,
            "pending": pending_migrations,
            "total_applied": len([m for m in applied_migrations if m["success"]]),
            "total_available": len(available_migrations),
            "total_pending": len(pending_migrations)
        }
    
    def validate_database_schema(self) -> Dict:
        """Valide l'intégrité du schéma de base de données"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            # Vérifier les tables essentielles
            essential_tables = [
                'users', 'boutique', 'customer', 'campaign', 
                'product', 'stored_images', 'migration_history'
            ]
            
            missing_tables = [table for table in essential_tables if table not in tables]
            
            # Vérifier les contraintes importantes
            constraints_check = []
            for table in essential_tables:
                if table in tables:
                    try:
                        foreign_keys = inspector.get_foreign_keys(table)
                        indexes = inspector.get_indexes(table)
                        constraints_check.append({
                            "table": table,
                            "foreign_keys": len(foreign_keys),
                            "indexes": len(indexes),
                            "status": "ok"
                        })
                    except Exception as e:
                        constraints_check.append({
                            "table": table,
                            "status": "error",
                            "error": str(e)
                        })
            
            return {
                "valid": len(missing_tables) == 0,
                "total_tables": len(tables),
                "essential_tables": len(essential_tables),
                "missing_tables": missing_tables,
                "constraints": constraints_check
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation du schéma: {str(e)}")
            return {
                "valid": False,
                "error": str(e)
            }

def run_ci_migrations():
    """Fonction principale pour CI/CD"""
    try:
        manager = MigrationManager()
        
        # Valider le schéma existant
        schema_validation = manager.validate_database_schema()
        print(f"Validation du schéma: {'✓' if schema_validation['valid'] else '✗'}")
        
        if not schema_validation['valid']:
            print(f"Erreurs de schéma: {schema_validation.get('missing_tables', [])}")
            if schema_validation.get('error'):
                print(f"Erreur: {schema_validation['error']}")
        
        # Exécuter les migrations
        results = manager.run_pending_migrations()
        
        print(f"\n=== Résultats des migrations ===")
        print(f"Total: {results['total']}")
        print(f"Appliquées: {len(results['applied'])}")
        print(f"Ignorées: {len(results['skipped'])}")
        print(f"Échecs: {len(results['failed'])}")
        
        if results['applied']:
            print(f"\nMigrations appliquées:")
            for migration in results['applied']:
                print(f"  ✓ {migration}")
        
        if results['failed']:
            print(f"\nMigrations échouées:")
            for failure in results['failed']:
                print(f"  ✗ {failure['migration']}: {failure['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Erreur fatale dans run_ci_migrations: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_ci_migrations()
    sys.exit(0 if success else 1)
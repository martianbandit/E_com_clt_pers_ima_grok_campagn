"""
Système de sauvegarde automatique pour la base de données PostgreSQL
Utilise APScheduler pour programmer les sauvegardes périodiques
"""

import os
import subprocess
import logging
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

class BackupManager:
    """Gestionnaire des sauvegardes automatiques de la base de données"""
    
    def __init__(self, backup_dir="backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.scheduler = None
        self.max_backups = int(os.environ.get("MAX_BACKUPS", "7"))  # Garder 7 jours par défaut
        
    def start_scheduler(self):
        """Démarre le planificateur de sauvegardes"""
        if self.scheduler is not None:
            logger.warning("Scheduler already running")
            return
            
        self.scheduler = BackgroundScheduler()
        
        # Sauvegarde quotidienne à 2h du matin
        self.scheduler.add_job(
            func=self.create_backup,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_backup',
            name='Daily Database Backup',
            replace_existing=True
        )
        
        # Sauvegarde de test immédiate (si configuré)
        if os.environ.get("BACKUP_ON_START", "false").lower() == "true":
            self.scheduler.add_job(
                func=self.create_backup,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=30),
                id='startup_backup',
                name='Startup Test Backup'
            )
        
        try:
            self.scheduler.start()
            logger.info("Backup scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start backup scheduler: {str(e)}")
    
    def stop_scheduler(self):
        """Arrête le planificateur"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
            logger.info("Backup scheduler stopped")
    
    def create_backup(self):
        """Crée une sauvegarde de la base de données"""
        try:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                logger.error("DATABASE_URL not configured")
                return False
            
            # Générer le nom du fichier de sauvegarde
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"ninjalead_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            compressed_path = self.backup_dir / f"{backup_filename}.gz"
            
            logger.info(f"Starting database backup to {backup_path}")
            
            # Commande pg_dump
            cmd = [
                "pg_dump",
                database_url,
                "--no-password",
                "--verbose",
                "--clean",
                "--no-acl",
                "--no-owner",
                "-f", str(backup_path)
            ]
            
            # Exécuter la sauvegarde
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                logger.error(f"pg_dump failed: {result.stderr}")
                return False
            
            # Compresser le fichier
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Supprimer le fichier non compressé
            backup_path.unlink()
            
            # Vérifier la taille du fichier compressé
            file_size = compressed_path.stat().st_size
            if file_size == 0:
                logger.error("Backup file is empty")
                compressed_path.unlink()
                return False
            
            logger.info(f"Backup created successfully: {compressed_path} ({file_size} bytes)")
            
            # Nettoyer les anciennes sauvegardes
            self.cleanup_old_backups()
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Backup timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Backup failed with error: {str(e)}")
            return False
    
    def cleanup_old_backups(self):
        """Supprime les anciennes sauvegardes au-delà de la limite"""
        try:
            backup_files = list(self.backup_dir.glob("ninjalead_backup_*.sql.gz"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(backup_files) > self.max_backups:
                files_to_delete = backup_files[self.max_backups:]
                for file_path in files_to_delete:
                    file_path.unlink()
                    logger.info(f"Deleted old backup: {file_path}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")
    
    def list_backups(self):
        """Liste toutes les sauvegardes disponibles"""
        backup_files = list(self.backup_dir.glob("ninjalead_backup_*.sql.gz"))
        backups = []
        
        for backup_file in backup_files:
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime),
                "age_days": (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            })
        
        # Trier par date de création (plus récent en premier)
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups
    
    def restore_backup(self, backup_filename):
        """Restaure une sauvegarde spécifique"""
        try:
            backup_path = self.backup_dir / backup_filename
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                logger.error("DATABASE_URL not configured")
                return False
            
            # Décompresser temporairement
            temp_sql_path = backup_path.with_suffix('')  # Enlever .gz
            
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_sql_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            logger.info(f"Starting database restore from {backup_filename}")
            
            # Commande psql pour restaurer
            cmd = [
                "psql",
                database_url,
                "--quiet",
                "-f", str(temp_sql_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            # Nettoyer le fichier temporaire
            temp_sql_path.unlink()
            
            if result.returncode != 0:
                logger.error(f"Database restore failed: {result.stderr}")
                return False
            
            logger.info("Database restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed with error: {str(e)}")
            return False
    
    def get_backup_status(self):
        """Retourne le statut du système de sauvegarde"""
        backups = self.list_backups()
        
        status = {
            "enabled": self.scheduler is not None and self.scheduler.running,
            "backup_directory": str(self.backup_dir),
            "max_backups": self.max_backups,
            "total_backups": len(backups),
            "last_backup": None,
            "next_backup": None,
            "disk_usage": {
                "total_size": sum(b["size"] for b in backups),
                "average_size": sum(b["size"] for b in backups) // len(backups) if backups else 0
            }
        }
        
        if backups:
            status["last_backup"] = {
                "filename": backups[0]["filename"],
                "created": backups[0]["created"].isoformat(),
                "size": backups[0]["size"],
                "age_hours": (datetime.now() - backups[0]["created"]).total_seconds() / 3600
            }
        
        if self.scheduler and self.scheduler.running:
            job = self.scheduler.get_job('daily_backup')
            if job:
                status["next_backup"] = job.next_run_time.isoformat() if job.next_run_time else None
        
        return status

# Instance globale du gestionnaire de sauvegarde
backup_manager = BackupManager()

def init_backup_system():
    """Initialise le système de sauvegarde"""
    try:
        # Vérifier si pg_dump est disponible
        result = subprocess.run(["pg_dump", "--version"], capture_output=True, timeout=10)
        if result.returncode != 0:
            logger.error("pg_dump not available - backup system disabled")
            return False
        
        backup_manager.start_scheduler()
        logger.info("Backup system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize backup system: {str(e)}")
        return False

def shutdown_backup_system():
    """Arrête proprement le système de sauvegarde"""
    backup_manager.stop_scheduler()
    logger.info("Backup system shutdown complete")
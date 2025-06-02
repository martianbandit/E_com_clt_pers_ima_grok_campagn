"""
Configuration pour la réplication read-only de la base de données
Optimisé pour les requêtes analytics et reporting
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseReplicationManager:
    """Gestionnaire pour la réplication read-only de la base de données"""
    
    def __init__(self):
        self.master_url = os.environ.get("DATABASE_URL")
        self.replica_url = os.environ.get("DATABASE_REPLICA_URL")
        
        # Configuration des engines
        self.master_engine = None
        self.replica_engine = None
        
        # Sessions
        self.MasterSession = None
        self.ReplicaSession = None
        
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialise les connexions master et replica"""
        try:
            if not self.master_url:
                logger.error("DATABASE_URL non configurée")
                return False
            
            # Engine principal (écriture)
            self.master_engine = create_engine(
                self.master_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            
            # Engine replica (lecture seule)
            if self.replica_url:
                self.replica_engine = create_engine(
                    self.replica_url,
                    poolclass=QueuePool,
                    pool_size=15,  # Plus de connexions pour analytics
                    max_overflow=30,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    echo=False
                )
                logger.info("Réplication read-only configurée")
            else:
                # Fallback sur master si pas de replica
                self.replica_engine = self.master_engine
                logger.warning("DATABASE_REPLICA_URL non configurée - utilisation du master pour les lectures")
            
            # Sessions
            self.MasterSession = sessionmaker(bind=self.master_engine)
            self.ReplicaSession = sessionmaker(bind=self.replica_engine)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des connexions: {str(e)}")
            return False
    
    @contextmanager
    def get_read_session(self):
        """Context manager pour les sessions de lecture (replica)"""
        session = self.ReplicaSession()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur dans session read-only: {str(e)}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_write_session(self):
        """Context manager pour les sessions d'écriture (master)"""
        session = self.MasterSession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur dans session write: {str(e)}")
            raise
        finally:
            session.close()
    
    def execute_analytics_query(self, query, params=None):
        """Exécute une requête analytics sur la replica"""
        try:
            with self.get_read_session() as session:
                if params:
                    result = session.execute(text(query), params)
                else:
                    result = session.execute(text(query))
                return result.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête analytics: {str(e)}")
            return []
    
    def get_database_stats(self):
        """Retourne les statistiques des bases de données"""
        stats = {
            "master": {"status": "unknown", "connections": 0},
            "replica": {"status": "unknown", "connections": 0}
        }
        
        try:
            # Stats master
            with self.master_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        count(*) as active_connections,
                        pg_database_size(current_database()) as db_size_bytes
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                row = result.fetchone()
                stats["master"] = {
                    "status": "healthy",
                    "active_connections": row[0],
                    "db_size_bytes": row[1],
                    "db_size_mb": round(row[1] / (1024 * 1024), 2)
                }
        except Exception as e:
            logger.error(f"Erreur stats master: {str(e)}")
            stats["master"]["status"] = "error"
        
        try:
            # Stats replica (si différente du master)
            if self.replica_url and self.replica_engine != self.master_engine:
                with self.replica_engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT 
                            count(*) as active_connections,
                            CASE 
                                WHEN pg_is_in_recovery() THEN 'replica'
                                ELSE 'master'
                            END as role
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """))
                    row = result.fetchone()
                    stats["replica"] = {
                        "status": "healthy",
                        "active_connections": row[0],
                        "role": row[1],
                        "is_replica": row[1] == 'replica'
                    }
            else:
                stats["replica"] = stats["master"].copy()
                stats["replica"]["note"] = "Same as master (no replica configured)"
                
        except Exception as e:
            logger.error(f"Erreur stats replica: {str(e)}")
            stats["replica"]["status"] = "error"
        
        return stats
    
    def test_replication_lag(self):
        """Teste le délai de réplication"""
        if not self.replica_url or self.replica_engine == self.master_engine:
            return {"lag_seconds": 0, "note": "No replica configured"}
        
        try:
            # Créer un enregistrement de test sur master
            test_query = """
                INSERT INTO metrics (name, category, status, created_at) 
                VALUES ('replication_test', 'system', true, NOW()) 
                RETURNING id, created_at
            """
            
            with self.get_write_session() as master_session:
                result = master_session.execute(text(test_query))
                test_record = result.fetchone()
                test_id = test_record[0]
                master_time = test_record[1]
            
            # Vérifier sur replica avec retry
            import time
            max_retries = 5
            for attempt in range(max_retries):
                time.sleep(0.5)  # Attendre 500ms
                
                with self.get_read_session() as replica_session:
                    check_query = "SELECT created_at FROM metrics WHERE id = :test_id"
                    result = replica_session.execute(text(check_query), {"test_id": test_id})
                    replica_record = result.fetchone()
                    
                    if replica_record:
                        replica_time = replica_record[0]
                        lag_seconds = (replica_time - master_time).total_seconds()
                        
                        # Nettoyer l'enregistrement de test
                        with self.get_write_session() as cleanup_session:
                            cleanup_session.execute(text("DELETE FROM metrics WHERE id = :test_id"), {"test_id": test_id})
                        
                        return {
                            "lag_seconds": abs(lag_seconds),
                            "attempts": attempt + 1,
                            "status": "healthy" if abs(lag_seconds) < 1 else "slow"
                        }
            
            # Si pas trouvé après tous les essais
            return {
                "lag_seconds": None,
                "attempts": max_retries,
                "status": "error",
                "error": "Replication test record not found on replica"
            }
            
        except Exception as e:
            logger.error(f"Erreur test replication lag: {str(e)}")
            return {
                "lag_seconds": None,
                "status": "error",
                "error": str(e)
            }

# Instance globale
db_replication = DatabaseReplicationManager()

def get_analytics_data(query, params=None):
    """Fonction helper pour exécuter des requêtes analytics"""
    return db_replication.execute_analytics_query(query, params)

def get_user_analytics(user_id=None, days=30):
    """Récupère les analytics utilisateur sur la replica"""
    base_query = """
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as total_actions,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(CASE WHEN status = true THEN 1 ELSE 0 END) as success_rate
    FROM metrics 
    WHERE created_at >= NOW() - INTERVAL '%s days'
    """ % days
    
    if user_id:
        base_query += " AND user_id = :user_id"
        params = {"user_id": user_id}
    else:
        params = None
    
    base_query += " GROUP BY DATE(created_at) ORDER BY date DESC"
    
    return get_analytics_data(base_query, params)

def get_campaign_performance():
    """Analytics des performances de campagnes"""
    query = """
    SELECT 
        c.title,
        c.status,
        c.campaign_type,
        COUNT(DISTINCT c.customer_id) as unique_customers,
        c.created_at,
        c.sent_at
    FROM campaign c
    WHERE c.created_at >= NOW() - INTERVAL '30 days'
    GROUP BY c.id, c.title, c.status, c.campaign_type, c.created_at, c.sent_at
    ORDER BY c.created_at DESC
    """
    
    return get_analytics_data(query)
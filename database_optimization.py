"""
Optimisations de base de données pour NinjaLead.ai
Implémente le connection pooling et l'indexation optimisée
"""

import os
import logging
from sqlalchemy import create_engine, text, Index
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
from typing import Dict, List, Any
import psutil
import time

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Gestionnaire d'optimisations de base de données"""
    
    def __init__(self, database_url: str = None):
        """
        Initialise l'optimiseur de base de données
        
        Args:
            database_url: URL de connexion à la base de données
        """
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL non configurée")
        
        self.optimized_engine = None
        self.Session = None
        
    def create_optimized_engine(self) -> None:
        """Crée un moteur de base de données optimisé avec connection pooling"""
        try:
            # Configuration du pool de connexions optimisé
            pool_config = {
                'poolclass': QueuePool,
                'pool_size': 10,  # Nombre de connexions permanentes
                'max_overflow': 20,  # Connexions supplémentaires autorisées
                'pool_pre_ping': True,  # Vérification de la santé des connexions
                'pool_recycle': 3600,  # Recyclage des connexions après 1h
                'pool_timeout': 30,  # Timeout pour obtenir une connexion
                'echo': False,  # Logging SQL désactivé en production
            }
            
            # Configuration des paramètres de connexion PostgreSQL
            connect_args = {
                'connect_timeout': 10,
                'application_name': 'NinjaLead.ai',
                'options': '-c default_transaction_isolation=read_committed'
            }
            
            self.optimized_engine = create_engine(
                self.database_url,
                connect_args=connect_args,
                **pool_config
            )
            
            # Création du sessionmaker optimisé
            self.Session = sessionmaker(bind=self.optimized_engine)
            
            logger.info("Moteur de base de données optimisé créé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du moteur optimisé: {e}")
            raise
    
    def test_connection_pool(self) -> Dict[str, Any]:
        """Teste les performances du pool de connexions"""
        if not self.optimized_engine:
            self.create_optimized_engine()
        
        results = {
            'pool_size': self.optimized_engine.pool.size(),
            'checked_in': self.optimized_engine.pool.checkedin(),
            'checked_out': self.optimized_engine.pool.checkedout(),
            'overflow': self.optimized_engine.pool.overflow(),
            'connection_tests': []
        }
        
        # Test de performance des connexions
        for i in range(5):
            start_time = time.time()
            try:
                with self.optimized_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    connection_time = (time.time() - start_time) * 1000
                    results['connection_tests'].append({
                        'test': i + 1,
                        'time_ms': round(connection_time, 2),
                        'success': True
                    })
            except Exception as e:
                results['connection_tests'].append({
                    'test': i + 1,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def create_performance_indexes(self) -> List[str]:
        """Crée les index de performance pour les requêtes critiques"""
        if not self.optimized_engine:
            self.create_optimized_engine()
        
        indexes_created = []
        
        # Index critiques pour les performances
        critical_indexes = [
            # Users table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active ON users(email) WHERE active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users(last_login_at);",
            
            # Campaigns table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_owner_created ON campaigns(owner_id, created_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_boutique_status ON campaigns(boutique_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_updated_at ON campaigns(updated_at);",
            
            # Products table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_owner_created ON products(owner_id, created_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_status ON products(status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_price ON products(price);",
            
            # Boutiques table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boutiques_owner_active ON boutiques(owner_id) WHERE active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boutiques_created_at ON boutiques(created_at);",
            
            # GDPR tables
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gdpr_request_user_status ON gdpr_request(user_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gdpr_request_created ON gdpr_request(created_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_consent_record_user_purpose ON consent_record(user_id, purpose);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_user_action ON audit_log(user_id, action);",
            
            # Metrics table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_category_status ON metrics(category, status);",
            
            # OSP Analysis table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_analysis_owner_type ON osp_analysis(owner_id, analysis_type);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_analysis_created ON osp_analysis(created_at);",
        ]
        
        try:
            with self.optimized_engine.connect() as conn:
                for index_sql in critical_indexes:
                    try:
                        conn.execute(text(index_sql))
                        conn.commit()
                        index_name = index_sql.split("IF NOT EXISTS ")[1].split(" ON ")[0]
                        indexes_created.append(index_name)
                        logger.info(f"Index créé: {index_name}")
                    except Exception as e:
                        logger.warning(f"Erreur lors de la création d'index: {e}")
                        
        except Exception as e:
            logger.error(f"Erreur lors de la création des index: {e}")
            
        return indexes_created
    
    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyse les performances des requêtes critiques"""
        if not self.optimized_engine:
            self.create_optimized_engine()
        
        # Requêtes critiques à analyser
        critical_queries = {
            'user_login': """
                SELECT id, email, password_hash, active 
                FROM users 
                WHERE email = 'test@example.com' AND active = true
            """,
            'user_campaigns': """
                SELECT c.*, b.name as boutique_name 
                FROM campaigns c 
                LEFT JOIN boutiques b ON c.boutique_id = b.id 
                WHERE c.owner_id = 'test_user' 
                ORDER BY c.updated_at DESC 
                LIMIT 10
            """,
            'recent_products': """
                SELECT * FROM products 
                WHERE owner_id = 'test_user' AND status = 'active' 
                ORDER BY created_at DESC 
                LIMIT 20
            """,
            'gdpr_requests': """
                SELECT * FROM gdpr_request 
                WHERE user_id = 'test_user' AND status = 'pending' 
                ORDER BY created_at DESC
            """
        }
        
        performance_results = {}
        
        try:
            with self.optimized_engine.connect() as conn:
                for query_name, query_sql in critical_queries.items():
                    try:
                        # Analyse EXPLAIN pour la requête
                        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query_sql}"
                        result = conn.execute(text(explain_sql))
                        explain_data = result.fetchone()[0]
                        
                        performance_results[query_name] = {
                            'execution_time_ms': explain_data[0]['Execution Time'],
                            'planning_time_ms': explain_data[0]['Planning Time'],
                            'total_cost': explain_data[0]['Plan']['Total Cost'],
                            'rows_returned': explain_data[0]['Plan'].get('Actual Rows', 0),
                            'analysis': explain_data[0]
                        }
                    except Exception as e:
                        performance_results[query_name] = {
                            'error': str(e),
                            'status': 'failed'
                        }
                        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des performances: {e}")
            
        return performance_results
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la base de données"""
        if not self.optimized_engine:
            self.create_optimized_engine()
        
        stats = {}
        
        try:
            with self.optimized_engine.connect() as conn:
                # Statistiques générales
                db_size_result = conn.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                           current_database() as db_name
                """))
                db_info = db_size_result.fetchone()
                stats['database'] = {
                    'name': db_info.db_name,
                    'size': db_info.db_size
                }
                
                # Statistiques des tables principales
                table_stats_result = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables 
                    ORDER BY n_live_tup DESC
                """))
                
                stats['tables'] = []
                for row in table_stats_result:
                    stats['tables'].append({
                        'name': row.tablename,
                        'inserts': row.inserts,
                        'updates': row.updates,
                        'deletes': row.deletes,
                        'live_tuples': row.live_tuples,
                        'dead_tuples': row.dead_tuples,
                        'last_vacuum': str(row.last_vacuum) if row.last_vacuum else None,
                        'last_analyze': str(row.last_analyze) if row.last_analyze else None
                    })
                
                # Statistiques des connexions
                connections_result = conn.execute(text("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """))
                
                conn_info = connections_result.fetchone()
                stats['connections'] = {
                    'total': conn_info.total_connections,
                    'active': conn_info.active_connections,
                    'idle': conn_info.idle_connections
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            stats['error'] = str(e)
            
        return stats
    
    def optimize_database_settings(self) -> Dict[str, Any]:
        """Optimise les paramètres de la base de données"""
        if not self.optimized_engine:
            self.create_optimized_engine()
        
        optimizations = []
        
        # Paramètres d'optimisation PostgreSQL
        optimization_queries = [
            # Augmenter la mémoire partagée
            "ALTER SYSTEM SET shared_buffers = '256MB';",
            # Optimiser les checkpoints
            "ALTER SYSTEM SET checkpoint_completion_target = 0.9;",
            # Améliorer les performances des requêtes
            "ALTER SYSTEM SET effective_cache_size = '1GB';",
            # Optimiser les connexions
            "ALTER SYSTEM SET max_connections = 100;",
            # Améliorer les statistiques
            "ALTER SYSTEM SET default_statistics_target = 100;",
        ]
        
        try:
            with self.optimized_engine.connect() as conn:
                for query in optimization_queries:
                    try:
                        conn.execute(text(query))
                        setting_name = query.split("SET ")[1].split(" =")[0]
                        optimizations.append(f"Optimisé: {setting_name}")
                    except Exception as e:
                        optimizations.append(f"Erreur: {e}")
                
                # Recharger la configuration
                try:
                    conn.execute(text("SELECT pg_reload_conf();"))
                    optimizations.append("Configuration rechargée")
                except Exception as e:
                    optimizations.append(f"Erreur lors du rechargement: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {e}")
            optimizations.append(f"Erreur générale: {e}")
            
        return {
            'optimizations_applied': optimizations,
            'timestamp': time.time(),
            'status': 'completed' if not any('Erreur' in opt for opt in optimizations) else 'partial'
        }

def run_database_optimization():
    """Exécute l'optimisation complète de la base de données"""
    print("🚀 Démarrage de l'optimisation de la base de données...")
    
    try:
        optimizer = DatabaseOptimizer()
        
        # 1. Création du moteur optimisé
        print("📊 Création du moteur de base de données optimisé...")
        optimizer.create_optimized_engine()
        
        # 2. Test du pool de connexions
        print("🔗 Test du pool de connexions...")
        pool_results = optimizer.test_connection_pool()
        print(f"   Pool size: {pool_results['pool_size']}")
        print(f"   Connexions actives: {pool_results['checked_out']}")
        print(f"   Connexions disponibles: {pool_results['checked_in']}")
        
        # 3. Création des index de performance
        print("📈 Création des index de performance...")
        indexes = optimizer.create_performance_indexes()
        print(f"   {len(indexes)} index créés")
        
        # 4. Analyse des performances
        print("🔍 Analyse des performances des requêtes...")
        performance = optimizer.analyze_query_performance()
        print(f"   {len(performance)} requêtes analysées")
        
        # 5. Statistiques de la base de données
        print("📊 Récupération des statistiques...")
        stats = optimizer.get_database_stats()
        if 'database' in stats:
            print(f"   Taille de la base: {stats['database']['size']}")
            print(f"   Nombre de tables: {len(stats.get('tables', []))}")
        
        # 6. Optimisation des paramètres
        print("⚙️ Optimisation des paramètres de la base de données...")
        optimization_results = optimizer.optimize_database_settings()
        print(f"   Statut: {optimization_results['status']}")
        
        print("✅ Optimisation de la base de données terminée avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'optimisation: {e}")
        return False

if __name__ == "__main__":
    run_database_optimization()
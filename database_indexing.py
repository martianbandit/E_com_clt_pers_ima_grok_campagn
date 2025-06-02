"""
Module d'optimisation et création d'index de base de données
Implémente l'indexation intelligente pour améliorer les performances des requêtes
"""

import logging
from typing import List, Dict, Any
from sqlalchemy import text, inspect
from flask import current_app
from app import db

logger = logging.getLogger(__name__)

class DatabaseIndexOptimizer:
    """Optimiseur d'index pour la base de données PostgreSQL"""
    
    def __init__(self):
        self.db = db
        
    def create_performance_indexes(self):
        """Crée les index optimisés pour les performances"""
        try:
            with self.db.engine.connect() as conn:
                # Index pour les utilisateurs
                self._create_user_indexes(conn)
                
                # Index pour les campagnes
                self._create_campaign_indexes(conn)
                
                # Index pour les produits
                self._create_product_indexes(conn)
                
                # Index pour les clients
                self._create_customer_indexes(conn)
                
                # Index pour les analyses OSP
                self._create_osp_indexes(conn)
                
                # Index pour l'audit et les logs
                self._create_audit_indexes(conn)
                
                # Index composites pour les requêtes complexes
                self._create_composite_indexes(conn)
                
                conn.commit()
                logger.info("Performance indexes created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create performance indexes: {e}")
            return False
        
        return True
    
    def _create_user_indexes(self, conn):
        """Crée les index pour la table User"""
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email ON \"user\" (email)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username ON \"user\" (username)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_created_at ON \"user\" (created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_last_seen ON \"user\" (last_seen)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_active ON \"user\" (is_active) WHERE is_active = true"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def _create_campaign_indexes(self, conn):
        """Crée les index pour la table Campaign"""
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_owner ON campaign (owner_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_customer ON campaign (customer_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_boutique ON campaign (boutique_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_created_at ON campaign (created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_status ON campaign (status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_active ON campaign (owner_id, created_at) WHERE status = 'active'"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def _create_product_indexes(self, conn):
        """Crée les index pour les tables Product et ImportedProduct"""
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_campaign ON product (campaign_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_owner ON product (owner_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_created_at ON product (created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_name_search ON product USING gin(to_tsvector('french', name))",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_imported_product_campaign ON imported_product (campaign_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_imported_product_owner ON imported_product (owner_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_imported_product_url ON imported_product (aliexpress_url)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def _create_customer_indexes(self, conn):
        """Crée les index pour la table Customer"""
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_owner ON customer (owner_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_created_at ON customer (created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_usage ON customer (usage_count)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_name_search ON customer USING gin(to_tsvector('french', name))"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def _create_osp_indexes(self, conn):
        """Crée les index pour la table OSPAnalysis"""
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_owner ON osp_analysis (owner_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_created_at ON osp_analysis (created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_url ON osp_analysis (url)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_domain ON osp_analysis (domain)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def _create_audit_indexes(self, conn):
        """Crée les index pour les tables d'audit"""
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_user ON audit_log (user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_action ON audit_log (action)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_user ON user_activity (user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_timestamp ON user_activity (timestamp)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def _create_composite_indexes(self, conn):
        """Crée des index composites pour les requêtes complexes"""
        indexes = [
            # Index composite pour les campagnes d'un utilisateur récentes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_user_recent ON campaign (owner_id, created_at DESC)",
            
            # Index composite pour les produits d'une campagne
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_campaign_created ON product (campaign_id, created_at DESC)",
            
            # Index composite pour l'historique utilisateur
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_user_time ON user_activity (user_id, timestamp DESC)",
            
            # Index composite pour les analyses OSP par utilisateur
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_osp_user_created ON osp_analysis (owner_id, created_at DESC)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyse les performances des requêtes courantes"""
        try:
            with self.db.engine.connect() as conn:
                # Requêtes de test pour mesurer les performances
                test_queries = {
                    'user_campaigns': """
                        EXPLAIN ANALYZE SELECT c.* FROM campaign c 
                        WHERE c.owner_id = 1 
                        ORDER BY c.created_at DESC 
                        LIMIT 10
                    """,
                    'campaign_products': """
                        EXPLAIN ANALYZE SELECT p.* FROM product p 
                        WHERE p.campaign_id = 1 
                        ORDER BY p.created_at DESC
                    """,
                    'user_activity': """
                        EXPLAIN ANALYZE SELECT ua.* FROM user_activity ua 
                        WHERE ua.user_id = 1 
                        ORDER BY ua.timestamp DESC 
                        LIMIT 20
                    """
                }
                
                results = {}
                for query_name, query_sql in test_queries.items():
                    try:
                        result = conn.execute(text(query_sql))
                        execution_plan = result.fetchall()
                        results[query_name] = {
                            'status': 'success',
                            'plan': [str(row) for row in execution_plan]
                        }
                    except Exception as e:
                        results[query_name] = {
                            'status': 'error',
                            'error': str(e)
                        }
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to analyze query performance: {e}")
            return {'error': str(e)}
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques d'utilisation des index"""
        try:
            with self.db.engine.connect() as conn:
                # Requête pour obtenir les statistiques des index
                stats_query = """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    ORDER BY idx_scan DESC
                """
                
                result = conn.execute(text(stats_query))
                index_stats = []
                
                for row in result:
                    index_stats.append({
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5]
                    })
                
                return {
                    'status': 'success',
                    'indexes': index_stats,
                    'total_indexes': len(index_stats)
                }
                
        except Exception as e:
            logger.error(f"Failed to get index statistics: {e}")
            return {'error': str(e)}
    
    def optimize_table_statistics(self):
        """Met à jour les statistiques des tables pour l'optimiseur de requêtes"""
        try:
            with self.db.engine.connect() as conn:
                # Tables principales à analyser
                tables = [
                    'user', 'campaign', 'product', 'imported_product', 
                    'customer', 'boutique', 'osp_analysis', 'user_activity', 'audit_log'
                ]
                
                for table in tables:
                    try:
                        # Use proper SQL identifier quoting to prevent SQL injection
                        conn.execute(text(f'ANALYZE "{table}"'))
                        logger.debug(f"Analyzed table: {table}")
                    except Exception as e:
                        logger.warning(f"Failed to analyze table {table}: {e}")
                
                conn.commit()
                logger.info("Table statistics updated successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to optimize table statistics: {e}")
            return False

# Instance globale
db_index_optimizer = DatabaseIndexOptimizer()
"""
Optimiseur de base de données pour NinjaLead.ai
Amélioration des performances des requêtes et gestion intelligente des connexions
"""

from sqlalchemy import event, create_engine, text
from sqlalchemy.pool import QueuePool
from flask_sqlalchemy import SQLAlchemy
import time
import logging
from contextlib import contextmanager
from performance_cache import cached_db_query, cache

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Optimiseur de performances pour les requêtes de base de données"""
    
    def __init__(self, app=None):
        self.app = app
        self.query_stats = {}
        
    def init_app(self, app, db):
        """Initialise les optimisations de base de données"""
        self.app = app
        self.db = db
        
        # Configuration avancée du pool de connexions
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'poolclass': QueuePool,
            'pool_size': 20,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'max_overflow': 30,
            'pool_timeout': 30,
        }
        
        # Événements pour surveiller les performances
        self._setup_query_monitoring()
        
        logger.info("Database optimizer initialized")
    
    def _setup_query_monitoring(self):
        """Configure la surveillance des requêtes"""
        
        @event.listens_for(self.db.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(self.db.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time
            
            # Enregistre les statistiques de requête
            query_type = statement.split()[0].upper() if statement else "UNKNOWN"
            
            if query_type not in self.query_stats:
                self.query_stats[query_type] = {
                    'count': 0,
                    'total_time': 0,
                    'max_time': 0,
                    'slow_queries': []
                }
            
            stats = self.query_stats[query_type]
            stats['count'] += 1
            stats['total_time'] += total
            stats['max_time'] = max(stats['max_time'], total)
            
            # Enregistre les requêtes lentes (> 1 seconde)
            if total > 1.0:
                slow_query = {
                    'statement': statement[:200] + '...' if len(statement) > 200 else statement,
                    'time': total,
                    'timestamp': time.time()
                }
                stats['slow_queries'].append(slow_query)
                
                # Garde seulement les 10 dernières requêtes lentes
                if len(stats['slow_queries']) > 10:
                    stats['slow_queries'] = stats['slow_queries'][-10:]
                
                logger.warning(f"Slow query detected: {total:.2f}s - {statement[:100]}...")
    
    @contextmanager
    def optimized_session(self):
        """Context manager pour des sessions optimisées"""
        session = self.db.session
        try:
            # Active les optimisations pour cette session
            session.execute(text("SET statement_timeout = '30s'"))
            session.execute(text("SET lock_timeout = '10s'"))
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_performance_stats(self):
        """Retourne les statistiques de performance"""
        stats = {}
        for query_type, data in self.query_stats.items():
            avg_time = data['total_time'] / data['count'] if data['count'] > 0 else 0
            stats[query_type] = {
                'count': data['count'],
                'avg_time': round(avg_time, 3),
                'max_time': round(data['max_time'], 3),
                'total_time': round(data['total_time'], 3),
                'slow_queries_count': len(data['slow_queries'])
            }
        return stats

# Décorateurs pour optimisations spécifiques
def bulk_insert_optimized(model_class, data_list, batch_size=1000):
    """Insertion en lot optimisée"""
    from app import db
    
    total_inserted = 0
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i + batch_size]
        try:
            db.session.bulk_insert_mappings(model_class, batch)
            db.session.commit()
            total_inserted += len(batch)
            logger.info(f"Inserted batch of {len(batch)} records")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk insert error: {e}")
            break
    
    return total_inserted

@cached_db_query(ttl=1800)  # Cache 30 minutes
def get_user_campaigns_optimized(user_id, limit=10):
    """Récupération optimisée des campagnes utilisateur"""
    from app import db
    from models import Campaign
    
    query = db.session.query(Campaign).filter(
        Campaign.owner_id == user_id
    ).order_by(
        Campaign.created_at.desc()
    ).limit(limit)
    
    return [campaign.to_dict() for campaign in query.all()]

@cached_db_query(ttl=600)  # Cache 10 minutes
def get_user_stats_optimized(user_id):
    """Statistiques utilisateur optimisées"""
    from app import db
    from models import Campaign, Customer, Product
    
    # Requête unique pour toutes les statistiques
    stats = db.session.execute(text("""
        SELECT 
            (SELECT COUNT(*) FROM campaign WHERE owner_id = :user_id) as campaigns_count,
            (SELECT COUNT(*) FROM customer WHERE owner_id = :user_id) as customers_count,
            (SELECT COUNT(*) FROM product WHERE owner_id = :user_id) as products_count,
            (SELECT COUNT(*) FROM campaign WHERE owner_id = :user_id AND created_at >= NOW() - INTERVAL '30 days') as recent_campaigns
    """), {"user_id": user_id}).fetchone()
    
    return {
        'campaigns_count': stats[0] or 0,
        'customers_count': stats[1] or 0,
        'products_count': stats[2] or 0,
        'recent_campaigns': stats[3] or 0
    }

def optimize_database_indexes():
    """Crée des index pour optimiser les performances"""
    from app import db
    
    index_queries = [
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_owner_created ON campaign(owner_id, created_at DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_owner_created ON customer(owner_id, created_at DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_owner_created ON product(owner_id, created_at DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_user_date ON user_activity(user_id, created_at DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_timestamp ON metric(timestamp DESC)",
    ]
    
    created_indexes = []
    for query in index_queries:
        try:
            db.session.execute(text(query))
            db.session.commit()
            index_name = query.split()[-1].split('(')[0]
            created_indexes.append(index_name)
            logger.info(f"Index created: {index_name}")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Index creation failed: {e}")
    
    return created_indexes

def analyze_database_performance():
    """Analyse les performances de la base de données"""
    from app import db
    
    try:
        # Analyse des tables les plus utilisées
        table_stats = db.session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows
            FROM pg_stat_user_tables 
            ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
            LIMIT 10
        """)).fetchall()
        
        # Analyse des index les plus utilisés
        index_stats = db.session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan as scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes 
            WHERE idx_scan > 0
            ORDER BY idx_scan DESC
            LIMIT 10
        """)).fetchall()
        
        return {
            'table_stats': [dict(row._mapping) for row in table_stats],
            'index_stats': [dict(row._mapping) for row in index_stats]
        }
        
    except Exception as e:
        logger.error(f"Database analysis error: {e}")
        return {"error": str(e)}

# Instance globale de l'optimiseur
db_optimizer = DatabaseOptimizer()
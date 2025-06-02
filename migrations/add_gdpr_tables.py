"""
Script de migration pour ajouter les tables GDPR de conformité
"""

import os
import sys
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, create_engine, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
import datetime

def run_migration():
    """Execute la migration pour ajouter les tables GDPR"""
    
    # Configuration de la base de données
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ Erreur: DATABASE_URL non définie")
        return False
    
    try:
        # Créer la connexion
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("✅ Connexion à la base de données établie")
            
            # Table GDPRRequest
            print("📋 Création de la table gdpr_request...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gdpr_request (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    request_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                    description TEXT,
                    specific_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    response_data JSONB,
                    response_file_path VARCHAR(255),
                    rejection_reason TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT
                );
            """))
            
            # Table ConsentRecord
            print("📋 Création de la table consent_record...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS consent_record (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    purpose VARCHAR(50) NOT NULL,
                    consent_given BOOLEAN NOT NULL,
                    consent_text TEXT NOT NULL,
                    consent_version VARCHAR(10) NOT NULL,
                    given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    withdrawn_at TIMESTAMP,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    consent_method VARCHAR(50) NOT NULL
                );
            """))
            
            # Table DataRetentionPolicy
            print("📋 Création de la table data_retention_policy...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS data_retention_policy (
                    id SERIAL PRIMARY KEY,
                    data_category VARCHAR(100) NOT NULL UNIQUE,
                    retention_period_days INTEGER NOT NULL,
                    legal_basis VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
            """))
            
            # Table AuditLog (si pas déjà créée)
            print("📋 Création de la table audit_log...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) DEFAULT 'medium' NOT NULL,
                    user_id INTEGER,
                    username VARCHAR(64),
                    session_id VARCHAR(100),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    endpoint VARCHAR(100),
                    http_method VARCHAR(10),
                    resource_type VARCHAR(50),
                    resource_id VARCHAR(50),
                    old_values JSONB,
                    new_values JSONB,
                    description TEXT NOT NULL,
                    metadata JSONB,
                    success BOOLEAN DEFAULT TRUE NOT NULL,
                    requires_attention BOOLEAN DEFAULT FALSE NOT NULL
                );
            """))
            
            # Index pour les performances
            print("📋 Création des index...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_gdpr_request_user_id ON gdpr_request(user_id);
                CREATE INDEX IF NOT EXISTS idx_gdpr_request_status ON gdpr_request(status);
                CREATE INDEX IF NOT EXISTS idx_gdpr_request_created_at ON gdpr_request(created_at);
                
                CREATE INDEX IF NOT EXISTS idx_consent_record_user_id ON consent_record(user_id);
                CREATE INDEX IF NOT EXISTS idx_consent_record_purpose ON consent_record(purpose);
                CREATE INDEX IF NOT EXISTS idx_consent_record_given_at ON consent_record(given_at);
                CREATE INDEX IF NOT EXISTS idx_consent_record_withdrawn_at ON consent_record(withdrawn_at);
                
                CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
                CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_log_severity ON audit_log(severity);
                CREATE INDEX IF NOT EXISTS idx_audit_log_requires_attention ON audit_log(requires_attention);
            """))
            
            # Insertion des politiques de rétention par défaut
            print("📋 Insertion des politiques de rétention par défaut...")
            conn.execute(text("""
                INSERT INTO data_retention_policy (data_category, retention_period_days, legal_basis, description)
                VALUES 
                    ('user_account', 2555, 'Legitimate interest - compte utilisateur', 'Données de compte utilisateur (nom, email, préférences)'),
                    ('marketing_data', 1095, 'Consent - marketing', 'Données marketing et communications'),
                    ('analytics_data', 730, 'Legitimate interest - amélioration du service', 'Données d''analyse et d''usage'),
                    ('security_logs', 365, 'Legitimate interest - sécurité', 'Logs de sécurité et d''audit'),
                    ('support_data', 1095, 'Legitimate interest - support client', 'Données de support et communication client')
                ON CONFLICT (data_category) DO NOTHING;
            """))
            
            # Validation des tables créées
            print("🔍 Vérification des tables créées...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('gdpr_request', 'consent_record', 'data_retention_policy', 'audit_log')
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            expected_tables = ['audit_log', 'consent_record', 'data_retention_policy', 'gdpr_request']
            
            for table in expected_tables:
                if table in tables:
                    print(f"✅ Table {table} créée avec succès")
                else:
                    print(f"❌ Table {table} non trouvée")
            
            # Commit des changements
            conn.commit()
            print("✅ Migration GDPR terminée avec succès!")
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Démarrage de la migration GDPR...")
    success = run_migration()
    
    if success:
        print("✅ Migration GDPR complétée avec succès!")
        sys.exit(0)
    else:
        print("❌ Migration GDPR échouée!")
        sys.exit(1)
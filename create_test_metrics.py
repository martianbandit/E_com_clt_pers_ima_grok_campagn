"""
Script pour créer des données de test pour les métriques
"""
import os
import sys
import random
import json
import logging
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from app import app, db  # Importer l'application et la BD déjà configurées

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_test_metrics(count=50):
    """Génère des métriques de test aléatoires"""
    from models import Metric
    
    categories = ['ai', 'generation', 'user', 'system', 'import', None]
    names = [
        'generate_text', 'generate_image', 'generate_json', 'summarize_text',
        'analyze_image', 'translate_text', 'extract_keywords', 'check_sentiment',
        'user_login', 'user_registration', 'user_profile_update', 'product_import',
        'database_backup', 'system_health_check', 'file_upload', 'file_download'
    ]
    statuses = [True, True, True, True, True, False]  # 5/6 chance de succès
    
    # Date de début (7 jours avant aujourd'hui)
    start_date = datetime.now() - timedelta(days=7)
    
    metrics_generated = 0
    
    with app.app_context():
        # Vérifier si des métriques existent déjà
        existing_count = Metric.query.count()
        if existing_count > 0:
            logging.info(f"Il y a déjà {existing_count} métriques dans la base de données.")
            choice = input("Voulez-vous quand même générer de nouvelles métriques? (y/n): ")
            if choice.lower() != 'y':
                logging.info("Génération annulée.")
                return
        
        # Générer les métriques
        for i in range(count):
            name = random.choice(names)
            category = random.choice(categories)
            status = random.choice(statuses)
            execution_time = round(random.uniform(0.1, 5.0), 2) if status else round(random.uniform(5.0, 15.0), 2)
            
            # Date aléatoire entre start_date et maintenant
            days_offset = random.randint(0, 7)
            hours_offset = random.randint(0, 23)
            minutes_offset = random.randint(0, 59)
            created_at = start_date + timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
            
            # Données supplémentaires en fonction du type de métrique
            data = {}
            if name == 'generate_text':
                data = {
                    'model': random.choice(['grok-2', 'gpt-4o']),
                    'tokens': random.randint(100, 1000),
                    'prompt_length': random.randint(10, 200)
                }
            elif name == 'generate_image':
                data = {
                    'model': random.choice(['dall-e-3', 'midjourney']),
                    'size': random.choice(['1024x1024', '512x512']),
                    'quality': random.choice(['standard', 'hd'])
                }
            elif name == 'user_login':
                data = {
                    'user_id': random.randint(1, 10),
                    'device': random.choice(['desktop', 'mobile', 'tablet']),
                    'browser': random.choice(['chrome', 'firefox', 'safari'])
                }
            
            # Ajouter une erreur si le statut est False
            if not status:
                if name.startswith('generate'):
                    data['error'] = random.choice([
                        'API timeout', 'Invalid parameters', 'Rate limit exceeded',
                        'Server error', 'Authentication failed'
                    ])
                else:
                    data['error'] = random.choice([
                        'Database connection error', 'Invalid input', 'Permission denied',
                        'Resource not found', 'Server error'
                    ])
            
            # Créer la métrique
            metric = Metric(
                name=name,
                category=category,
                status=status,
                execution_time=execution_time,
                data=data,
                created_at=created_at,
                # Ajouter le champ response_time également pour avoir des données complètes
                response_time=round(execution_time * 1000, 2)  # Convertir en ms
            )
            
            db.session.add(metric)
            metrics_generated += 1
            
            # Commit toutes les 10 métriques pour économiser la mémoire
            if i % 10 == 0:
                db.session.commit()
                logging.info(f"Généré {i+1} métriques...")
        
        # Commit final
        db.session.commit()
        logging.info(f"Génération terminée. {metrics_generated} métriques créées avec succès.")

if __name__ == "__main__":
    try:
        # Déterminer le nombre de métriques à générer
        count = 50
        if len(sys.argv) > 1:
            try:
                count = int(sys.argv[1])
            except ValueError:
                logging.error("Le nombre de métriques doit être un entier.")
                sys.exit(1)
        
        generate_test_metrics(count)
    except Exception as e:
        logging.error(f"Erreur lors de la génération des métriques de test: {e}")
        sys.exit(1)
"""
Script pour convertir les personas existants dans la table Customer 
vers le nouveau format structuré CustomerPersona
"""
import os
import sys
from datetime import datetime
import asyncio
import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Importer les modèles depuis le fichier models.py existant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import db, app
from models import Customer, CustomerPersona, CustomerPersonaAssociation, NicheMarket, Boutique
import persona_manager

async def run_conversion():
    """Execute la conversion des personas existants vers le nouveau format"""
    with app.app_context():
        # Récupérer les clients avec un persona existant
        customers_with_persona = Customer.query.filter(Customer.persona.isnot(None)).all()
        
        print(f"Trouvé {len(customers_with_persona)} clients avec un persona existant.")
        
        # Utiliser le gestionnaire de personas pour la conversion
        count = persona_manager.convert_legacy_personas()
        print(f"Conversion terminée. {count} personas ont été convertis et associés.")
        
        # Récupérer les statistiques
        stats = persona_manager.get_personas_stats()
        print(f"Statistiques des personas:")
        print(f"- Total des personas: {stats['total_personas']}")
        print(f"- Total des associations: {stats['total_associations']}")
        print(f"- Personas avec avatar: {stats['personas_with_avatar']}")
        print("- Personas par niche:")
        for niche, count in stats.get('personas_by_niche', {}).items():
            print(f"  - {niche}: {count}")
        print("- Personas par boutique:")
        for boutique, count in stats.get('personas_by_boutique', {}).items():
            print(f"  - {boutique}: {count}")

async def generate_sample_personas():
    """Génère des exemples de personas pour démonstration"""
    with app.app_context():
        # Créer un persona pour chaque niche existante
        niches = NicheMarket.query.all()
        
        for niche in niches:
            print(f"Création d'un persona pour la niche: {niche.name}")
            
            # Utiliser le nom de la niche pour créer un titre de persona
            title = f"Client type pour {niche.name}"
            
            # Créer une description basée sur les caractéristiques de la niche
            characteristics = niche.get_characteristics_list()
            characteristics_str = ", ".join(characteristics) if characteristics else "diverses caractéristiques"
            description = f"Un client idéal pour la niche {niche.name}, avec {characteristics_str} comme centres d'intérêt principaux."
            
            # Créer le persona
            persona = persona_manager.create_persona_from_text(
                title=title,
                description=description,
                niche_market_id=niche.id,
                additional_data={
                    'primary_goal': f"Trouver des produits de qualité dans la catégorie {niche.name}",
                    'pain_points': "Difficulté à trouver des produits authentiques et de qualité",
                    'buying_triggers': "Recommandations d'amis, avis positifs, offres spéciales",
                    'values': ["qualité", "authenticité", "durabilité"],
                    'interests': characteristics,
                    'lifestyle': "Mode de vie actif, intérêt pour les nouvelles tendances"
                }
            )
            
            print(f"Persona créé avec succès: {persona.title} (ID: {persona.id})")
            
            # Associer ce persona à un client existant de cette niche (s'il y en a)
            customer = Customer.query.filter_by(niche_market_id=niche.id).first()
            if customer:
                print(f"Association du persona au client {customer.name}")
                persona_manager.assign_persona_to_customer(
                    customer_id=customer.id,
                    persona_id=persona.id,
                    is_primary=True,
                    relevance_score=0.95,
                    notes="Persona généré automatiquement pour démonstration"
                )

async def main():
    """Fonction principale"""
    action = "convert"
    if len(sys.argv) > 1:
        action = sys.argv[1]
    
    if action == "convert":
        await run_conversion()
    elif action == "sample":
        await generate_sample_personas()
    elif action == "all":
        await run_conversion()
        await generate_sample_personas()
    else:
        print(f"Action inconnue: {action}")
        print("Usage: python convert_personas.py [convert|sample|all]")

if __name__ == "__main__":
    asyncio.run(main())
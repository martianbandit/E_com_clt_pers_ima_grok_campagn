"""
Script pour générer des personas clients et les associer aux profils clients existants
"""
import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Importer les modèles depuis le fichier models.py existant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import db, app
from models import Customer, CustomerPersona, CustomerPersonaAssociation, NicheMarket, Boutique

def create_persona(title, description, niche_market_id=None, boutique_id=None, additional_data=None):
    """Crée un nouveau persona"""
    # Valeurs par défaut pour les données supplémentaires
    data = {
        'primary_goal': "Trouver des produits de qualité et adaptés à ses besoins",
        'pain_points': "Difficulté à trouver des produits authentiques et de qualité",
        'buying_triggers': "Recommandations, avis positifs, offres spéciales",
        'values': ["qualité", "authenticité", "durabilité"],
        'interests': ["mode", "design", "technologie"],
        'lifestyle': "Mode de vie actif, intérêt pour les nouvelles tendances"
    }
    
    # Mise à jour avec les données supplémentaires fournies
    if additional_data:
        data.update(additional_data)
    
    # Créer le persona
    persona = CustomerPersona(
        title=title,
        description=description,
        primary_goal=data.get('primary_goal'),
        pain_points=data.get('pain_points'),
        buying_triggers=data.get('buying_triggers'),
        age_range=data.get('age_range'),
        gender_affinity=data.get('gender_affinity'),
        location_type=data.get('location_type'),
        income_bracket=data.get('income_bracket'),
        education_level=data.get('education_level'),
        values=data.get('values'),
        interests=data.get('interests'),
        lifestyle=data.get('lifestyle'),
        personality_traits=data.get('personality_traits'),
        buying_habits=data.get('buying_habits'),
        brand_affinities=data.get('brand_affinities'),
        price_sensitivity=data.get('price_sensitivity'),
        decision_factors=data.get('decision_factors'),
        preferred_channels=data.get('preferred_channels'),
        content_preferences=data.get('content_preferences'),
        social_media_behavior=data.get('social_media_behavior'),
        niche_specific_attributes=data.get('niche_specific_attributes'),
        custom_fields=data.get('custom_fields'),
        avatar_url=data.get('avatar_url'),
        avatar_prompt=data.get('avatar_prompt'),
        niche_market_id=niche_market_id,
        boutique_id=boutique_id
    )
    
    db.session.add(persona)
    db.session.commit()
    return persona

def assign_persona(customer_id, persona_id, is_primary=True, relevance_score=None, notes=None):
    """Assigne un persona à un client"""
    # Vérifier si l'association existe déjà
    existing = CustomerPersonaAssociation.query.filter_by(
        customer_id=customer_id,
        persona_id=persona_id
    ).first()
    
    if existing:
        # Mettre à jour l'association existante
        existing.is_primary = is_primary
        if relevance_score is not None:
            existing.relevance_score = relevance_score
        if notes:
            existing.notes = notes
        db.session.commit()
        return existing
    
    # Si on définit comme persona principal, désactiver les autres
    if is_primary:
        CustomerPersonaAssociation.query.filter_by(
            customer_id=customer_id,
            is_primary=True
        ).update({"is_primary": False})
    
    # Créer la nouvelle association
    association = CustomerPersonaAssociation(
        customer_id=customer_id,
        persona_id=persona_id,
        is_primary=is_primary,
        relevance_score=relevance_score or 1.0,
        notes=notes
    )
    
    db.session.add(association)
    db.session.commit()
    return association

def generate_personas_for_niches():
    """Génère des personas pour chaque niche de marché"""
    with app.app_context():
        # Récupérer toutes les niches
        niches = NicheMarket.query.all()
        print(f"Génération de personas pour {len(niches)} niches de marché")
        
        for niche in niches:
            print(f"Traitement de la niche: {niche.name}")
            
            # Créer un persona générique pour cette niche
            title = f"Client idéal pour {niche.name}"
            description = f"Persona représentant le client idéal pour la niche {niche.name}."
            
            # Attributs spécifiques à la niche
            characteristics = niche.get_characteristics_list()
            
            try:
                persona = create_persona(
                    title=title,
                    description=description,
                    niche_market_id=niche.id,
                    additional_data={
                        'interests': characteristics,
                        'niche_specific_attributes': {
                            'niche_name': niche.name,
                            'key_characteristics': characteristics
                        }
                    }
                )
                
                print(f"Persona créé: {persona.title} (ID: {persona.id})")
                
                # Associer ce persona à quelques clients de cette niche
                customers = Customer.query.filter_by(niche_market_id=niche.id).limit(3).all()
                for customer in customers:
                    try:
                        assign_persona(
                            customer_id=customer.id,
                            persona_id=persona.id,
                            is_primary=True,
                            notes=f"Persona générique pour la niche {niche.name}"
                        )
                        print(f"Persona assigné au client: {customer.name}")
                    except Exception as e:
                        print(f"Erreur lors de l'assignation du persona au client {customer.id}: {e}")
                        db.session.rollback()
                
            except Exception as e:
                print(f"Erreur lors de la création du persona pour la niche {niche.id}: {e}")
                db.session.rollback()
        
        print("Génération de personas terminée.")

def generate_common_personas():
    """Génère des personas communs qui peuvent être utilisés pour différentes niches"""
    with app.app_context():
        common_personas = [
            {
                "title": "Acheteur Économe",
                "description": "Ce persona représente un client attentif à son budget, qui recherche des offres et des promotions, et qui privilégie le rapport qualité-prix.",
                "primary_goal": "Trouver des produits de qualité au meilleur prix",
                "pain_points": "Difficulté à trouver des produits abordables sans compromettre la qualité",
                "price_sensitivity": "élevée",
                "buying_triggers": "Promotions, ventes flash, codes de réduction, programmes de fidélité"
            },
            {
                "title": "Amateur de Luxe",
                "description": "Ce persona représente un client à fort pouvoir d'achat qui privilégie l'exclusivité, la qualité premium et le service personnalisé.",
                "primary_goal": "Découvrir des produits exclusifs et de haute qualité",
                "pain_points": "Manque d'options véritablement haut de gamme et personnalisées",
                "price_sensitivity": "faible",
                "buying_triggers": "Éditions limitées, service exclusif, nouveautés, qualité artisanale"
            },
            {
                "title": "Acheteur Éthique et Durable",
                "description": "Ce persona représente un client soucieux de l'impact environnemental et social de ses achats, privilégiant les marques engagées.",
                "primary_goal": "Consommer de manière responsable et éthique",
                "pain_points": "Difficulté à trouver des produits véritablement durables avec une transparence complète",
                "values": ["durabilité", "éthique", "responsabilité sociale", "écologie"],
                "buying_triggers": "Certifications éthiques, production locale, transparence de la chaîne d'approvisionnement"
            },
            {
                "title": "Technophile Précoce",
                "description": "Ce persona représente un client passionné par la technologie et l'innovation, toujours à l'affût des dernières tendances.",
                "primary_goal": "Découvrir et adopter les innovations avant tout le monde",
                "pain_points": "Obsolescence rapide des produits, manque d'options vraiment innovantes",
                "interests": ["technologie", "gadgets", "innovation", "science"],
                "buying_triggers": "Nouvelles technologies, fonctionnalités innovantes, éditions de lancement"
            }
        ]
        
        print(f"Génération de {len(common_personas)} personas communs")
        
        for persona_data in common_personas:
            try:
                persona = create_persona(
                    title=persona_data["title"],
                    description=persona_data["description"],
                    additional_data=persona_data
                )
                
                print(f"Persona commun créé: {persona.title} (ID: {persona.id})")
                
                # Assigner à quelques clients au hasard
                customers = Customer.query.order_by(db.func.random()).limit(2).all()
                for customer in customers:
                    try:
                        assign_persona(
                            customer_id=customer.id,
                            persona_id=persona.id,
                            is_primary=False,  # Ne pas remplacer le persona principal
                            relevance_score=0.7,  # Score de pertinence plus faible
                            notes=f"Persona commun: {persona_data['title']}"
                        )
                        print(f"Persona commun assigné au client: {customer.name}")
                    except Exception as e:
                        print(f"Erreur lors de l'assignation du persona commun au client {customer.id}: {e}")
                        db.session.rollback()
            
            except Exception as e:
                print(f"Erreur lors de la création du persona commun {persona_data['title']}: {e}")
                db.session.rollback()
        
        print("Génération de personas communs terminée.")

def display_persona_stats():
    """Affiche des statistiques sur les personas dans le système"""
    with app.app_context():
        total_personas = CustomerPersona.query.count()
        total_associations = CustomerPersonaAssociation.query.count()
        
        print(f"Statistiques des personas:")
        print(f"- Nombre total de personas: {total_personas}")
        print(f"- Nombre total d'associations: {total_associations}")
        
        # Personas par niche
        personas_by_niche = db.session.query(
            NicheMarket.name, 
            db.func.count(CustomerPersona.id)
        ).outerjoin(
            CustomerPersona, 
            NicheMarket.id == CustomerPersona.niche_market_id
        ).group_by(
            NicheMarket.name
        ).all()
        
        print("- Personas par niche:")
        for niche_name, count in personas_by_niche:
            print(f"  - {niche_name or 'Sans niche'}: {count}")
        
        # Clients avec plusieurs personas
        customer_counts = db.session.query(
            db.func.count(CustomerPersonaAssociation.persona_id).label('persona_count'),
            db.func.count(db.func.distinct(CustomerPersonaAssociation.customer_id)).label('customer_count')
        ).group_by(
            CustomerPersonaAssociation.customer_id
        ).all()
        
        customers_with_multiple = sum(1 for count in customer_counts if count[0] > 1)
        print(f"- Clients avec plusieurs personas: {customers_with_multiple}")
        
        # Personas principaux vs secondaires
        primary_count = CustomerPersonaAssociation.query.filter_by(is_primary=True).count()
        secondary_count = CustomerPersonaAssociation.query.filter_by(is_primary=False).count()
        
        print(f"- Personas principaux: {primary_count}")
        print(f"- Personas secondaires: {secondary_count}")

def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage: python generate_personas.py [niches|common|stats|all]")
        return
    
    action = sys.argv[1]
    
    if action == "niches":
        generate_personas_for_niches()
    elif action == "common":
        generate_common_personas()
    elif action == "stats":
        display_persona_stats()
    elif action == "all":
        generate_personas_for_niches()
        generate_common_personas()
        display_persona_stats()
    else:
        print(f"Action inconnue: {action}")
        print("Usage: python generate_personas.py [niches|common|stats|all]")

if __name__ == "__main__":
    main()
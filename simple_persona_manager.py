"""
Module simplifié pour la gestion des personas - compatible avec la structure existante
"""
from app import db
from models import Customer, CustomerPersona, CustomerPersonaAssociation
import logging

def get_customer_personas_simple(customer_id):
    """
    Récupère les personas associés à un client de manière simple
    """
    try:
        # Vérifier si le client existe
        customer = Customer.query.get(customer_id)
        if not customer:
            return []
        
        # Récupérer les associations de personas
        associations = CustomerPersonaAssociation.query.filter_by(customer_id=customer_id).all()
        
        personas_data = []
        for assoc in associations:
            if assoc.persona:
                personas_data.append({
                    'association_id': assoc.id,
                    'persona_id': assoc.persona.id,
                    'title': assoc.persona.title or 'Persona sans titre',
                    'description': assoc.persona.description or 'Aucune description',
                    'is_primary': assoc.is_primary,
                    'relevance_score': assoc.relevance_score or 1.0,
                    'notes': assoc.notes or '',
                    'created_at': assoc.created_at.isoformat() if assoc.created_at else None,
                    'avatar_url': assoc.persona.avatar_url
                })
        
        return personas_data
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des personas du client {customer_id}: {str(e)}")
        return []

def create_simple_persona(customer_id, title=None, description=None):
    """
    Crée un persona simple à partir des données d'un client
    """
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError("Client non trouvé")
        
        # Générer un titre par défaut si non fourni
        if not title:
            title = f"Persona pour {customer.name}"
        
        # Générer une description par défaut si non fournie
        if not description:
            description = f"Persona basé sur le profil de {customer.name}"
            if customer.persona:
                description = customer.persona[:200] + "..." if len(customer.persona) > 200 else customer.persona
        
        # Créer le persona avec des valeurs par défaut
        persona = CustomerPersona(
            title=title,
            description=description,
            age_range=f"{customer.age-5}-{customer.age+5}" if customer.age else None,
            gender_affinity=customer.gender,
            location_type="Urbain" if customer.location else None,
            income_bracket=customer.income_level,
            education_level=customer.education,
            interests=customer.interests,
            avatar_url=customer.avatar_url,
            niche_market_id=customer.niche_market_id,
            boutique_id=customer.boutique_id
        )
        
        db.session.add(persona)
        db.session.flush()  # Pour obtenir l'ID
        
        # Créer l'association
        association = CustomerPersonaAssociation(
            customer_id=customer_id,
            persona_id=persona.id,
            is_primary=True,
            relevance_score=1.0,
            notes="Persona généré automatiquement"
        )
        
        db.session.add(association)
        db.session.commit()
        
        return {
            'id': persona.id,
            'title': persona.title,
            'description': persona.description,
            'avatar_url': persona.avatar_url
        }
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la création du persona pour le client {customer_id}: {str(e)}")
        raise e

def get_personas_stats_simple():
    """
    Récupère des statistiques simples sur les personas
    """
    try:
        total_personas = CustomerPersona.query.count()
        total_associations = CustomerPersonaAssociation.query.count()
        personas_with_avatar = CustomerPersona.query.filter(CustomerPersona.avatar_url.isnot(None)).count()
        
        return {
            'total_personas': total_personas,
            'total_associations': total_associations,
            'personas_with_avatar': personas_with_avatar
        }
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        return {
            'total_personas': 0,
            'total_associations': 0,
            'personas_with_avatar': 0
        }

def assign_persona_simple(customer_id, persona_id, is_primary=False, relevance_score=1.0, notes=""):
    """
    Assigne un persona à un client de manière simple
    """
    try:
        # Vérifier que le client et le persona existent
        customer = Customer.query.get(customer_id)
        persona = CustomerPersona.query.get(persona_id)
        
        if not customer or not persona:
            raise ValueError("Client ou persona non trouvé")
        
        # Vérifier si l'association existe déjà
        existing = CustomerPersonaAssociation.query.filter_by(
            customer_id=customer_id,
            persona_id=persona_id
        ).first()
        
        if existing:
            # Mettre à jour l'association existante
            existing.is_primary = is_primary
            existing.relevance_score = relevance_score
            existing.notes = notes
            association = existing
        else:
            # Si on définit comme principal, désactiver les autres
            if is_primary:
                CustomerPersonaAssociation.query.filter_by(
                    customer_id=customer_id,
                    is_primary=True
                ).update({"is_primary": False})
            
            # Créer une nouvelle association
            association = CustomerPersonaAssociation(
                customer_id=customer_id,
                persona_id=persona_id,
                is_primary=is_primary,
                relevance_score=relevance_score,
                notes=notes
            )
            db.session.add(association)
        
        db.session.commit()
        return association.id
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de l'assignation du persona {persona_id} au client {customer_id}: {str(e)}")
        raise e

def search_personas_simple(criteria):
    """
    Recherche simple de personas selon des critères
    """
    try:
        query = CustomerPersona.query
        
        # Recherche par titre
        if criteria.get('title'):
            query = query.filter(CustomerPersona.title.ilike(f"%{criteria['title']}%"))
        
        # Recherche par tranche d'âge
        if criteria.get('age_range'):
            query = query.filter(CustomerPersona.age_range == criteria['age_range'])
        
        # Recherche par genre
        if criteria.get('gender_affinity'):
            query = query.filter(CustomerPersona.gender_affinity == criteria['gender_affinity'])
        
        # Recherche par niveau de revenus
        if criteria.get('income_bracket'):
            query = query.filter(CustomerPersona.income_bracket == criteria['income_bracket'])
        
        # Recherche dans la description
        if criteria.get('description_keywords'):
            keywords = criteria['description_keywords'].split()
            for keyword in keywords:
                query = query.filter(CustomerPersona.description.ilike(f"%{keyword}%"))
        
        personas = query.limit(10).all()
        
        personas_data = []
        for persona in personas:
            personas_data.append({
                'id': persona.id,
                'title': persona.title,
                'description': persona.description,
                'age_range': persona.age_range,
                'gender_affinity': persona.gender_affinity,
                'income_bracket': persona.income_bracket,
                'interests': persona.interests,
                'avatar_url': persona.avatar_url
            })
        
        return personas_data
        
    except Exception as e:
        logging.error(f"Erreur lors de la recherche de personas: {str(e)}")
        return []
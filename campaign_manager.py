"""
Module de gestion des campagnes marketing avec métriques intégrées
"""
import os
import time
import logging
import datetime
from typing import Dict, List, Optional, Union, Any

from flask import current_app
from sqlalchemy import func

from app import db, log_metric
from models import Campaign, Customer, CustomerPersona, Boutique, Metric
from ai_utils import AIManager

class CampaignManager:
    """
    Gestionnaire centralisé pour les campagnes marketing
    avec journalisation intégrée des performances et métriques
    """
    
    def __init__(self):
        """Initialiser le gestionnaire de campagnes"""
        self.ai_manager = AIManager(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            xai_api_key=os.environ.get("XAI_API_KEY")
        )
        
        # Types de campagnes supportés
        self.campaign_types = {
            "email": {"name": "Email", "description": "Campagnes marketing par e-mail"},
            "social": {"name": "Social Media", "description": "Posts pour réseaux sociaux"},
            "ad": {"name": "Advertisement", "description": "Publicités textuelles"},
            "sms": {"name": "SMS", "description": "Messages marketing courts pour SMS"},
            "product_description": {"name": "Product Description", "description": "Descriptions de produits"}
        }
        
    def create_campaign(self, 
                      title: str, 
                      campaign_type: str,
                      profile_data: Dict = None, 
                      customer_id: int = None,
                      persona_id: int = None,
                      boutique_id: int = None,
                      image_prompt: str = None,
                      platforms: List[str] = None,
                      scheduled_at: datetime.datetime = None,
                      target_audience: str = None) -> Campaign:
        """
        Crée une nouvelle campagne et génère son contenu avec l'IA
        
        Args:
            title: Titre de la campagne
            campaign_type: Type de campagne
            profile_data: Données du profil client (si client en session)
            customer_id: ID du client (DB) si applicable
            persona_id: ID du persona client si applicable
            boutique_id: ID de la boutique associée si applicable
            image_prompt: Prompt pour générer une image (optionnel)
            platforms: Liste des plateformes de publication
            scheduled_at: Date planifiée de publication
            target_audience: Description de l'audience cible
            
        Returns:
            Objet Campaign créé
        """
        start_time = time.time()
        
        # Vérifier que le type de campagne est valide
        if campaign_type not in self.campaign_types:
            raise ValueError(f"Type de campagne non supporté: {campaign_type}")
        
        # Récupérer les objets liés si IDs fournis
        customer = None
        persona = None
        boutique = None
        
        if customer_id:
            customer = Customer.query.get(customer_id)
            if not customer:
                raise ValueError(f"Client introuvable: ID {customer_id}")
            
            # Si profile_data non fourni, l'extraire du client
            if not profile_data:
                profile_data = customer.profile_data if customer.profile_data else {
                    'name': customer.name,
                    'age': customer.age,
                    'location': customer.location,
                    'gender': customer.gender,
                    'language': customer.language,
                    'interests': customer.get_interests_list(),
                    'preferred_device': customer.preferred_device,
                    'persona': customer.persona
                }
        
        if persona_id:
            persona = CustomerPersona.query.get(persona_id)
            if not persona:
                raise ValueError(f"Persona introuvable: ID {persona_id}")
        
        if boutique_id:
            boutique = Boutique.query.get(boutique_id)
            if not boutique:
                raise ValueError(f"Boutique introuvable: ID {boutique_id}")
                
        try:
            # Générer le contenu marketing avec l'IA
            generation_start = time.time()
            prompt = self._build_campaign_prompt(
                title=title,
                campaign_type=campaign_type,
                profile_data=profile_data,
                customer=customer,
                campaign_persona=persona,
                campaign_boutique=boutique,
                target_audience=target_audience
            )
            
            # Calculer le temps de génération du prompt
            prompt_time = (time.time() - generation_start) * 1000
            
            # Générer le contenu
            content = self.ai_manager.generate_text(
                prompt=prompt,
                metric_name="campaign_content_generation",
                customer_id=customer_id if customer else None
            )
            
            # Calculer le temps de génération du contenu
            content_generation_time = (time.time() - generation_start) * 1000
            
            # Générer une image si demandé
            image_url = None
            image_generation_data = None
            
            if image_prompt:
                try:
                    image_generation_start = time.time()
                    image_url = self.ai_manager.generate_image(
                        prompt=image_prompt,
                        metric_name="campaign_image_generation",
                        customer_id=customer_id if customer else None
                    )
                    
                    # Métadonnées sur la génération d'image
                    image_generation_data = {
                        "prompt": image_prompt,
                        "generation_time_ms": (time.time() - image_generation_start) * 1000,
                        "success": image_url is not None
                    }
                except Exception as img_error:
                    logging.error(f"Error generating image for campaign: {str(img_error)}")
                    image_generation_data = {
                        "prompt": image_prompt,
                        "error": str(img_error),
                        "success": False
                    }
            
            # Créer l'objet Campaign
            campaign = Campaign(
                title=title,
                content=content,
                campaign_type=campaign_type,
                profile_data=profile_data,
                customer_id=customer_id,
                persona_id=persona_id,
                boutique_id=boutique_id,
                prompt_used=prompt,
                ai_model_used=self.ai_manager.grok_client and "grok" or "openai",
                status="draft",
                image_url=image_url,
                image_prompt=image_prompt,
                platforms=platforms,
                scheduled_at=scheduled_at,
                target_audience=target_audience,
                generation_params={
                    "prompt_generation_time_ms": prompt_time,
                    "content_generation_time_ms": content_generation_time,
                    "total_generation_time_ms": (time.time() - start_time) * 1000,
                    "image_generation": image_generation_data
                }
            )
            
            # Enregistrer la campagne
            db.session.add(campaign)
            db.session.commit()
            
            # Journaliser la métrique
            log_metric(
                metric_name="campaign_creation",
                category="generation",
                status="success",
                data={
                    "campaign_id": campaign.id,
                    "campaign_type": campaign_type,
                    "title": title,
                    "customer_id": customer_id,
                    "persona_id": persona_id,
                    "boutique_id": boutique_id,
                    "has_image": image_url is not None,
                    "total_time_ms": (time.time() - start_time) * 1000
                },
                response_time=(time.time() - start_time) * 1000,
                customer_id=customer_id
            )
            
            return campaign
            
        except Exception as e:
            # Journaliser l'erreur
            log_metric(
                metric_name="campaign_creation",
                category="generation",
                status="error",
                data={
                    "error": str(e),
                    "campaign_type": campaign_type,
                    "title": title,
                    "customer_id": customer_id,
                    "persona_id": persona_id,
                    "boutique_id": boutique_id
                },
                response_time=(time.time() - start_time) * 1000,
                customer_id=customer_id
            )
            
            # Ré-lever l'exception
            raise
            
    def _build_campaign_prompt(self, title, campaign_type, profile_data=None, 
                              customer=None, persona=None, boutique=None,
                              target_audience=None) -> str:
        """
        Construit un prompt optimisé pour générer le contenu de la campagne
        
        Returns:
            Prompt optimisé pour l'IA
        """
        # Instructions de base selon le type de campagne
        campaign_instructions = {
            "email": (
                "Créez un email marketing personnalisé qui s'adresse directement au client. "
                "L'email doit inclure : objet, salutation, introduction, corps avec bénéfices clés, "
                "appel à l'action clair, et signature. Utilisez un ton chaleureux et professionnel."
            ),
            "social": (
                "Créez une publication pour réseau social percutante et engageante. "
                "Elle doit être concise (max 280 caractères pour Twitter), inclure des hashtags pertinents, "
                "un appel à l'action et être rédigée dans un style conversationnel."
            ),
            "ad": (
                "Rédigez une publicité texte persuasive avec un titre accrocheur (max 30 caractères), "
                "un corps concis mettant en avant les bénéfices clés (max 90 caractères), "
                "et un appel à l'action fort (max 15 caractères)."
            ),
            "sms": (
                "Créez un SMS marketing court et efficace (max 160 caractères) avec un message clair, "
                "une proposition de valeur et un appel à l'action concis. Incluez la possibilité de "
                "désabonnement conformément aux réglementations."
            ),
            "product_description": (
                "Rédigez une description de produit optimisée pour le e-commerce. "
                "Elle doit inclure : un titre accrocheur, une introduction captivante, "
                "les caractéristiques principales avec leurs bénéfices, des détails techniques "
                "si pertinents, et pourquoi le client devrait acheter maintenant."
            )
        }
        
        # Construire le prompt de base
        prompt = f"Titre de la campagne: {title}\n\n"
        prompt += f"Type de campagne: {self.campaign_types[campaign_type]['name']}\n\n"
        prompt += f"Instructions: {campaign_instructions[campaign_type]}\n\n"
        
        # Ajouter les informations du client/persona
        if profile_data:
            prompt += "Profil client:\n"
            prompt += f"- Nom: {profile_data.get('name', 'Non spécifié')}\n"
            prompt += f"- Âge: {profile_data.get('age', 'Non spécifié')}\n"
            prompt += f"- Localisation: {profile_data.get('location', 'Non spécifiée')}\n"
            prompt += f"- Genre: {profile_data.get('gender', 'Non spécifié')}\n"
            prompt += f"- Langue: {profile_data.get('language', 'Non spécifiée')}\n"
            
            # Intérêts
            interests = profile_data.get('interests', [])
            if interests:
                if isinstance(interests, list):
                    prompt += f"- Intérêts: {', '.join(interests)}\n"
                else:
                    prompt += f"- Intérêts: {interests}\n"
            
            # Persona
            persona_text = profile_data.get('persona')
            if persona_text:
                prompt += f"\nPersona du client:\n{persona_text}\n"
        
        # Ajouter les informations du persona (depuis la base de données)
        if persona:
            prompt += f"\nPersona détaillé:\n"
            prompt += f"- Titre: {persona.title}\n"
            prompt += f"- Description: {persona.description}\n"
            
            if persona.primary_goal:
                prompt += f"- Objectif principal: {persona.primary_goal}\n"
            
            if persona.pain_points:
                prompt += f"- Points douloureux: {persona.pain_points}\n"
            
            if persona.buying_habits:
                prompt += f"- Habitudes d'achat: {persona.buying_habits}\n"
        
        # Ajouter les informations de la boutique
        if boutique:
            prompt += f"\nBoutique:\n"
            prompt += f"- Nom: {boutique.name}\n"
            prompt += f"- Description: {boutique.description}\n"
            
            if boutique.target_demographic:
                prompt += f"- Cible démographique: {boutique.target_demographic}\n"
        
        # Ajouter l'audience cible si spécifiée
        if target_audience:
            prompt += f"\nAudience cible: {target_audience}\n"
        
        # Instructions finales
        prompt += "\nConsignes générales:\n"
        prompt += "1. Adopter un ton correspondant à la marque et à la cible\n"
        prompt += "2. Utiliser un langage clair, concis et accrocheur\n"
        prompt += "3. Adapter le contenu aux caractéristiques et intérêts du client\n"
        prompt += "4. Intégrer une proposition de valeur unique et convaincante\n"
        prompt += "5. Inclure un appel à l'action clair et incitant à l'engagement\n"
        
        return prompt
        
    def get_campaign_metrics(self, campaign_id=None, campaign_type=None, date_range=None):
        """
        Récupère les métriques des campagnes avec filtres optionnels
        
        Args:
            campaign_id: ID spécifique d'une campagne (optionnel)
            campaign_type: Type de campagne (optionnel)
            date_range: Tuple (date_debut, date_fin) pour filtrer (optionnel)
            
        Returns:
            Dictionnaire de métriques et statistiques
        """
        # Base de la requête
        query = Campaign.query
        
        # Appliquer les filtres
        if campaign_id:
            query = query.filter_by(id=campaign_id)
        if campaign_type:
            query = query.filter_by(campaign_type=campaign_type)
        if date_range:
            start_date, end_date = date_range
            query = query.filter(Campaign.created_at >= start_date, Campaign.created_at <= end_date)
            
        # Récupérer les données
        campaigns = query.all()
        
        # Métriques d'engagement
        total_views = sum(campaign.view_count for campaign in campaigns)
        total_clicks = sum(campaign.click_count for campaign in campaigns)
        total_conversions = sum(campaign.conversion_count for campaign in campaigns)
        
        # Calcul des taux
        engagement_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        
        # Regrouper par type de campagne
        campaigns_by_type = {}
        for c in campaigns:
            if c.campaign_type not in campaigns_by_type:
                campaigns_by_type[c.campaign_type] = 0
            campaigns_by_type[c.campaign_type] += 1
            
        # Métriques liées aux appels d'API pour ces campagnes
        campaign_ids = [c.id for c in campaigns]
        api_metrics = None
        
        if campaign_ids:
            metrics_query = db.session.query(
                func.count(Metric.id).label('total_count'),
                func.sum(Metric.response_time).label('total_response_time'),
                func.avg(Metric.response_time).label('avg_response_time')
            ).filter(
                Metric.name == 'campaign_content_generation',
                Metric.data['campaign_id'].astext.cast(db.Integer).in_(campaign_ids)
            ).first()
            
            api_metrics = {
                'total_api_calls': metrics_query.total_count or 0,
                'avg_response_time_ms': metrics_query.avg_response_time or 0
            }
        
        return {
            'campaigns_count': len(campaigns),
            'total_views': total_views,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'engagement_rate': engagement_rate,
            'conversion_rate': conversion_rate,
            'campaigns_by_type': campaigns_by_type,
            'api_metrics': api_metrics
        }
        
    def regenerate_campaign_content(self, campaign_id, new_prompt=None):
        """
        Régénère le contenu d'une campagne existante
        
        Args:
            campaign_id: ID de la campagne à régénérer
            new_prompt: Nouveau prompt à utiliser (optionnel)
            
        Returns:
            Campagne mise à jour
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campagne introuvable: ID {campaign_id}")
            
        # Utiliser soit le nouveau prompt fourni, soit celui sauvegardé
        prompt = new_prompt or campaign.prompt_used
        if not prompt:
            raise ValueError("Aucun prompt disponible pour la régénération")
            
        start_time = time.time()
        
        try:
            # Générer le nouveau contenu
            new_content = self.ai_manager.generate_text(
                prompt=prompt,
                metric_name="campaign_content_regeneration",
                customer_id=campaign.customer_id
            )
            
            # Mettre à jour la campagne
            campaign.content = new_content
            campaign.updated_at = datetime.datetime.utcnow()
            
            if new_prompt:
                campaign.prompt_used = new_prompt
            
            db.session.commit()
            
            # Journaliser la métrique
            log_metric(
                metric_name="campaign_regeneration",
                category="generation",
                status="success",
                data={
                    "campaign_id": campaign.id,
                    "campaign_type": campaign.campaign_type,
                    "total_time_ms": (time.time() - start_time) * 1000
                },
                response_time=(time.time() - start_time) * 1000,
                customer_id=campaign.customer_id
            )
            
            return campaign
            
        except Exception as e:
            # Journaliser l'erreur
            log_metric(
                metric_name="campaign_regeneration",
                category="generation",
                status="error",
                data={
                    "error": str(e),
                    "campaign_id": campaign.id,
                    "campaign_type": campaign.campaign_type
                },
                response_time=(time.time() - start_time) * 1000,
                customer_id=campaign.customer_id
            )
            
            # Ré-lever l'exception
            raise
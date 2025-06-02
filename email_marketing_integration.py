"""
Intégration email marketing avec SendGrid
Gestion des campagnes email automatisées
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import requests
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

logger = logging.getLogger(__name__)

class EmailMarketingManager:
    """Gestionnaire des campagnes email marketing"""
    
    def __init__(self):
        self.sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('FROM_EMAIL', 'no-reply@ninjalead.ai')
        self.from_name = os.environ.get('FROM_NAME', 'NinjaLead.ai')
        
        if self.sendgrid_api_key:
            self.enabled = True
            self.base_url = 'https://api.sendgrid.com/v3'
            self.headers = {
                'Authorization': f'Bearer {self.sendgrid_api_key}',
                'Content-Type': 'application/json'
            }
            logger.info("SendGrid email marketing initialized")
        else:
            self.enabled = False
            logger.warning("SendGrid non configuré - clé API manquante")
    
    def send_single_email(self, 
                         to_email: str,
                         subject: str,
                         html_content: str,
                         text_content: str = None,
                         template_id: str = None,
                         dynamic_data: Dict = None) -> bool:
        """Envoyer un email simple"""
        if not self.enabled:
            logger.warning("Tentative d'envoi email sans configuration SendGrid")
            return False
        
        try:
            payload = {
                "personalizations": [{
                    "to": [{"email": to_email}],
                    "dynamic_template_data": dynamic_data or {}
                }],
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                }
            }
            
            if template_id:
                payload["template_id"] = template_id
            else:
                payload["subject"] = subject
                payload["content"] = [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
                if text_content:
                    payload["content"].append({
                        "type": "text/plain",
                        "value": text_content
                    })
            
            response = requests.post(
                f"{self.base_url}/mail/send",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 202:
                logger.info(f"Email envoyé avec succès à {to_email}")
                return True
            else:
                logger.error(f"Erreur envoi email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception envoi email: {str(e)}")
            return False
    
    def create_contact_list(self, list_name: str) -> Optional[str]:
        """Créer une liste de contacts"""
        if not self.enabled:
            return None
        
        try:
            payload = {"name": list_name}
            
            response = requests.post(
                f"{self.base_url}/marketing/lists",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                list_data = response.json()
                logger.info(f"Liste créée: {list_name} (ID: {list_data['id']})")
                return list_data['id']
            else:
                logger.error(f"Erreur création liste: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception création liste: {str(e)}")
            return None
    
    def add_contact_to_list(self, 
                           email: str,
                           list_id: str,
                           first_name: str = None,
                           last_name: str = None,
                           custom_fields: Dict = None) -> bool:
        """Ajouter un contact à une liste"""
        if not self.enabled:
            return False
        
        try:
            contact_data = {
                "email": email,
                "custom_fields": custom_fields or {}
            }
            
            if first_name:
                contact_data["first_name"] = first_name
            if last_name:
                contact_data["last_name"] = last_name
            
            payload = {
                "list_ids": [list_id],
                "contacts": [contact_data]
            }
            
            response = requests.put(
                f"{self.base_url}/marketing/contacts",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 202:
                logger.info(f"Contact ajouté: {email} à la liste {list_id}")
                return True
            else:
                logger.error(f"Erreur ajout contact: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception ajout contact: {str(e)}")
            return False
    
    def create_email_campaign(self,
                             title: str,
                             subject: str,
                             html_content: str,
                             list_ids: List[str],
                             sender_id: int = None) -> Optional[str]:
        """Créer une campagne email"""
        if not self.enabled:
            return None
        
        try:
            payload = {
                "title": title,
                "subject": subject,
                "html_content": html_content,
                "list_ids": list_ids,
                "sender_id": sender_id,
                "suppression_group_id": 1,  # Groupe de suppression par défaut
                "categories": ["marketing", "ninjalead"]
            }
            
            response = requests.post(
                f"{self.base_url}/marketing/campaigns",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                campaign_data = response.json()
                logger.info(f"Campagne créée: {title} (ID: {campaign_data['id']})")
                return campaign_data['id']
            else:
                logger.error(f"Erreur création campagne: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception création campagne: {str(e)}")
            return None
    
    def send_campaign(self, campaign_id: str) -> bool:
        """Envoyer une campagne"""
        if not self.enabled:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/marketing/campaigns/{campaign_id}/schedules/now",
                headers=self.headers
            )
            
            if response.status_code == 201:
                logger.info(f"Campagne envoyée: {campaign_id}")
                return True
            else:
                logger.error(f"Erreur envoi campagne: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception envoi campagne: {str(e)}")
            return False
    
    def get_campaign_stats(self, campaign_id: str) -> Optional[Dict]:
        """Récupérer les statistiques d'une campagne"""
        if not self.enabled:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/marketing/campaigns/{campaign_id}/stats",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur récupération stats: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception récupération stats: {str(e)}")
            return None
    
    def create_automation_sequence(self,
                                  name: str,
                                  trigger_type: str,
                                  emails: List[Dict]) -> Optional[str]:
        """Créer une séquence d'emails automatisée"""
        if not self.enabled:
            return None
        
        try:
            payload = {
                "name": name,
                "trigger": {
                    "type": trigger_type  # "list_added", "date_based", etc.
                },
                "emails": emails
            }
            
            response = requests.post(
                f"{self.base_url}/marketing/automations",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                automation_data = response.json()
                logger.info(f"Automation créée: {name}")
                return automation_data['id']
            else:
                logger.error(f"Erreur création automation: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception création automation: {str(e)}")
            return None
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Envoyer un email de bienvenue"""
        subject = "Bienvenue sur NinjaLead.ai ! 🥷"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #4a90e2;">Bienvenue {user_name} !</h1>
                
                <p>Nous sommes ravis de vous accueillir sur NinjaLead.ai, votre plateforme d'intelligence marketing alimentée par l'IA.</p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>Vos premiers pas :</h3>
                    <ul>
                        <li>Créez votre premier persona client</li>
                        <li>Générez une campagne marketing IA</li>
                        <li>Explorez nos outils d'analyse</li>
                    </ul>
                </div>
                
                <p>Besoin d'aide ? Notre équipe support est là pour vous accompagner.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://ninjalead.ai/dashboard" 
                       style="background: #4a90e2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Accéder au tableau de bord
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    Cordialement,<br>
                    L'équipe NinjaLead.ai
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Bienvenue {user_name} !
        
        Nous sommes ravis de vous accueillir sur NinjaLead.ai.
        
        Vos premiers pas :
        - Créez votre premier persona client
        - Générez une campagne marketing IA
        - Explorez nos outils d'analyse
        
        Accédez à votre tableau de bord : https://ninjalead.ai/dashboard
        
        L'équipe NinjaLead.ai
        """
        
        return self.send_single_email(user_email, subject, html_content, text_content)
    
    def send_campaign_report(self, user_email: str, campaign_data: Dict) -> bool:
        """Envoyer un rapport de campagne"""
        subject = f"Rapport de votre campagne : {campaign_data.get('title', 'Sans titre')}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #4a90e2;">Rapport de campagne</h1>
                
                <h2>{campaign_data.get('title', 'Campagne')}</h2>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>Résultats :</h3>
                    <p><strong>Statut :</strong> {campaign_data.get('status', 'En cours')}</p>
                    <p><strong>Créée le :</strong> {campaign_data.get('created_at', 'N/A')}</p>
                    <p><strong>Type :</strong> {campaign_data.get('campaign_type', 'Standard')}</p>
                </div>
                
                <p>Consultez le détail complet dans votre tableau de bord.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://ninjalead.ai/campaigns" 
                       style="background: #4a90e2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Voir toutes les campagnes
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_single_email(user_email, subject, html_content)

# Instance globale
email_marketing = EmailMarketingManager()

# Templates d'emails prédéfinis
EMAIL_TEMPLATES = {
    'welcome': {
        'subject': 'Bienvenue sur NinjaLead.ai ! 🥷',
        'description': 'Email de bienvenue pour nouveaux utilisateurs'
    },
    'campaign_report': {
        'subject': 'Rapport de votre campagne',
        'description': 'Rapport automatique de performance de campagne'
    },
    'trial_reminder': {
        'subject': 'Votre essai gratuit se termine bientôt',
        'description': 'Rappel de fin d\'essai gratuit'
    },
    'payment_success': {
        'subject': 'Paiement confirmé - Merci !',
        'description': 'Confirmation de paiement réussi'
    },
    'monthly_digest': {
        'subject': 'Votre résumé mensuel NinjaLead.ai',
        'description': 'Digest mensuel des performances'
    }
}
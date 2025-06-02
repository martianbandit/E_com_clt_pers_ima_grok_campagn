"""
Intégration complète email marketing avec Mailchimp et SendGrid
Gestion des campagnes, listes et automatisations email
"""

import os
import requests
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from models import User, Campaign, EmailCampaign, EmailList, EmailSubscriber
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)

# Blueprint pour l'email marketing
email_bp = Blueprint('email_marketing', __name__, url_prefix='/email')

# Configuration des services
MAILCHIMP_API_KEY = os.environ.get('MAILCHIMP_API_KEY')
MAILCHIMP_SERVER_PREFIX = os.environ.get('MAILCHIMP_SERVER_PREFIX', 'us1')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

class EmailMarketingManager:
    """Gestionnaire centralisé pour les campagnes email marketing"""
    
    def __init__(self):
        self.mailchimp_client = None
        self.sendgrid_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialise les clients API email"""
        # Configuration Mailchimp
        if MAILCHIMP_API_KEY:
            try:
                self.mailchimp_client = MailchimpMarketing.Client()
                self.mailchimp_client.set_config({
                    "api_key": MAILCHIMP_API_KEY,
                    "server": MAILCHIMP_SERVER_PREFIX
                })
                # Test de connexion
                response = self.mailchimp_client.ping.get()
                logger.info("Mailchimp connecté avec succès")
            except Exception as e:
                logger.error(f"Erreur connexion Mailchimp: {e}")
                self.mailchimp_client = None
        
        # Configuration SendGrid
        if SENDGRID_API_KEY:
            try:
                self.sendgrid_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
                logger.info("SendGrid connecté avec succès")
            except Exception as e:
                logger.error(f"Erreur connexion SendGrid: {e}")
                self.sendgrid_client = None
    
    def create_email_list(self, list_name, description="", provider='mailchimp'):
        """
        Crée une nouvelle liste email sur le provider choisi
        
        Args:
            list_name: Nom de la liste
            description: Description de la liste
            provider: 'mailchimp' ou 'sendgrid'
            
        Returns:
            dict: Informations de la liste créée
        """
        try:
            if provider == 'mailchimp' and self.mailchimp_client:
                response = self.mailchimp_client.lists.create_list({
                    "name": list_name,
                    "contact": {
                        "company": "NinjaLead.ai",
                        "address1": "123 Marketing Street",
                        "city": "Paris",
                        "state": "IDF",
                        "zip": "75001",
                        "country": "FR"
                    },
                    "permission_reminder": "Vous recevez cet email car vous vous êtes inscrit sur NinjaLead.ai",
                    "campaign_defaults": {
                        "from_name": "NinjaLead.ai",
                        "from_email": "noreply@ninjaleads.ai",
                        "subject": "",
                        "language": "fr"
                    },
                    "email_type_option": True
                })
                
                # Enregistrer en base de données
                email_list = EmailList(
                    name=list_name,
                    description=description,
                    provider=provider,
                    external_id=response['id'],
                    user_id=current_user.id,
                    created_at=datetime.utcnow()
                )
                db.session.add(email_list)
                db.session.commit()
                
                return {
                    'success': True,
                    'list_id': response['id'],
                    'list_name': list_name,
                    'provider': provider
                }
                
            elif provider == 'sendgrid' and self.sendgrid_client:
                data = {
                    "name": list_name
                }
                response = self.sendgrid_client.client.contactdb.lists.post(request_body=data)
                
                if response.status_code == 201:
                    list_data = json.loads(response.body)
                    
                    email_list = EmailList(
                        name=list_name,
                        description=description,
                        provider=provider,
                        external_id=str(list_data['id']),
                        user_id=current_user.id,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(email_list)
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'list_id': list_data['id'],
                        'list_name': list_name,
                        'provider': provider
                    }
            
            return {'success': False, 'error': f'Provider {provider} non disponible'}
            
        except Exception as e:
            logger.error(f"Erreur création liste email: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_subscriber(self, email, first_name="", last_name="", list_id="", provider='mailchimp'):
        """
        Ajoute un abonné à une liste email
        
        Args:
            email: Email de l'abonné
            first_name: Prénom
            last_name: Nom
            list_id: ID de la liste
            provider: Provider email
            
        Returns:
            dict: Résultat de l'ajout
        """
        try:
            if provider == 'mailchimp' and self.mailchimp_client:
                member_info = {
                    "email_address": email,
                    "status": "subscribed",
                    "merge_fields": {
                        "FNAME": first_name,
                        "LNAME": last_name
                    }
                }
                
                response = self.mailchimp_client.lists.add_list_member(list_id, member_info)
                
                # Enregistrer en base
                subscriber = EmailSubscriber(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    list_id=list_id,
                    provider=provider,
                    external_id=response.get('id'),
                    status='subscribed',
                    subscribed_at=datetime.utcnow()
                )
                db.session.add(subscriber)
                db.session.commit()
                
                return {'success': True, 'subscriber_id': response.get('id')}
                
            elif provider == 'sendgrid' and self.sendgrid_client:
                data = [
                    {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name
                    }
                ]
                
                response = self.sendgrid_client.client.contactdb.recipients.post(request_body=data)
                
                if response.status_code == 201:
                    recipient_data = json.loads(response.body)
                    
                    subscriber = EmailSubscriber(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        list_id=list_id,
                        provider=provider,
                        external_id=recipient_data['persisted_recipients'][0],
                        status='subscribed',
                        subscribed_at=datetime.utcnow()
                    )
                    db.session.add(subscriber)
                    db.session.commit()
                    
                    return {'success': True, 'subscriber_id': recipient_data['persisted_recipients'][0]}
            
            return {'success': False, 'error': f'Provider {provider} non disponible'}
            
        except Exception as e:
            logger.error(f"Erreur ajout abonné: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_email_campaign(self, campaign_name, subject, content, list_id, sender_id, provider='mailchimp'):
        """
        Crée une campagne email
        
        Args:
            campaign_name: Nom de la campagne
            subject: Sujet de l'email
            content: Contenu HTML de l'email
            list_id: ID de la liste destinataire
            sender_id: ID de l'expéditeur
            provider: Provider email
            
        Returns:
            dict: Informations de la campagne créée
        """
        try:
            if provider == 'mailchimp' and self.mailchimp_client:
                campaign_config = {
                    "type": "regular",
                    "recipients": {"list_id": list_id},
                    "settings": {
                        "subject_line": subject,
                        "title": campaign_name,
                        "from_name": "NinjaLead.ai",
                        "reply_to": "noreply@ninjaleads.ai"
                    }
                }
                
                # Créer la campagne
                campaign = self.mailchimp_client.campaigns.create(campaign_config)
                campaign_id = campaign['id']
                
                # Ajouter le contenu
                self.mailchimp_client.campaigns.set_content(campaign_id, {
                    "html": content
                })
                
                # Enregistrer en base
                email_campaign = EmailCampaign(
                    name=campaign_name,
                    subject=subject,
                    content=content,
                    list_id=list_id,
                    provider=provider,
                    external_id=campaign_id,
                    sender_id=sender_id,
                    status='draft',
                    created_at=datetime.utcnow()
                )
                db.session.add(email_campaign)
                db.session.commit()
                
                return {
                    'success': True,
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name,
                    'status': 'draft'
                }
                
            elif provider == 'sendgrid' and self.sendgrid_client:
                # SendGrid utilise des templates et des envois directs
                campaign_data = {
                    "name": campaign_name,
                    "subject": subject,
                    "sender_id": sender_id,
                    "list_ids": [int(list_id)],
                    "html_content": content,
                    "categories": ["ninjaleads", "marketing"]
                }
                
                response = self.sendgrid_client.client.campaigns.post(request_body=campaign_data)
                
                if response.status_code == 201:
                    campaign_info = json.loads(response.body)
                    
                    email_campaign = EmailCampaign(
                        name=campaign_name,
                        subject=subject,
                        content=content,
                        list_id=list_id,
                        provider=provider,
                        external_id=str(campaign_info['id']),
                        sender_id=sender_id,
                        status='draft',
                        created_at=datetime.utcnow()
                    )
                    db.session.add(email_campaign)
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'campaign_id': campaign_info['id'],
                        'campaign_name': campaign_name,
                        'status': 'draft'
                    }
            
            return {'success': False, 'error': f'Provider {provider} non disponible'}
            
        except Exception as e:
            logger.error(f"Erreur création campagne email: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_campaign(self, campaign_id, provider='mailchimp'):
        """
        Envoie une campagne email
        
        Args:
            campaign_id: ID de la campagne
            provider: Provider email
            
        Returns:
            dict: Résultat de l'envoi
        """
        try:
            if provider == 'mailchimp' and self.mailchimp_client:
                response = self.mailchimp_client.campaigns.send(campaign_id)
                
                # Mettre à jour le statut en base
                email_campaign = EmailCampaign.query.filter_by(
                    external_id=campaign_id,
                    provider=provider
                ).first()
                
                if email_campaign:
                    email_campaign.status = 'sent'
                    email_campaign.sent_at = datetime.utcnow()
                    db.session.commit()
                
                return {'success': True, 'status': 'sent'}
                
            elif provider == 'sendgrid' and self.sendgrid_client:
                response = self.sendgrid_client.client.campaigns._(campaign_id).schedules.now.post()
                
                if response.status_code == 201:
                    email_campaign = EmailCampaign.query.filter_by(
                        external_id=campaign_id,
                        provider=provider
                    ).first()
                    
                    if email_campaign:
                        email_campaign.status = 'sent'
                        email_campaign.sent_at = datetime.utcnow()
                        db.session.commit()
                    
                    return {'success': True, 'status': 'sent'}
            
            return {'success': False, 'error': f'Provider {provider} non disponible'}
            
        except Exception as e:
            logger.error(f"Erreur envoi campagne: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_campaign_stats(self, campaign_id, provider='mailchimp'):
        """
        Récupère les statistiques d'une campagne
        
        Args:
            campaign_id: ID de la campagne
            provider: Provider email
            
        Returns:
            dict: Statistiques de la campagne
        """
        try:
            if provider == 'mailchimp' and self.mailchimp_client:
                stats = self.mailchimp_client.reports.get_campaign_report(campaign_id)
                
                return {
                    'success': True,
                    'emails_sent': stats.get('emails_sent', 0),
                    'opens': stats.get('opens', {}).get('opens', 0),
                    'open_rate': stats.get('opens', {}).get('open_rate', 0),
                    'clicks': stats.get('clicks', {}).get('clicks', 0),
                    'click_rate': stats.get('clicks', {}).get('click_rate', 0),
                    'unsubscribes': stats.get('unsubscribed', 0),
                    'bounces': stats.get('bounces', {}).get('hard_bounces', 0)
                }
                
            elif provider == 'sendgrid' and self.sendgrid_client:
                response = self.sendgrid_client.client.campaigns._(campaign_id).stats.get()
                
                if response.status_code == 200:
                    stats = json.loads(response.body)
                    
                    return {
                        'success': True,
                        'emails_sent': stats.get('delivered', 0),
                        'opens': stats.get('opens', 0),
                        'open_rate': stats.get('open_rate', 0),
                        'clicks': stats.get('clicks', 0),
                        'click_rate': stats.get('click_rate', 0),
                        'unsubscribes': stats.get('unsubscribes', 0),
                        'bounces': stats.get('bounces', 0)
                    }
            
            return {'success': False, 'error': f'Provider {provider} non disponible'}
            
        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            return {'success': False, 'error': str(e)}

# Instance globale du gestionnaire
email_manager = EmailMarketingManager()

@email_bp.route('/')
@login_required
def dashboard():
    """Dashboard email marketing"""
    # Récupérer les listes et campagnes de l'utilisateur
    email_lists = EmailList.query.filter_by(user_id=current_user.id).all()
    email_campaigns = EmailCampaign.query.filter_by(sender_id=current_user.id).all()
    
    return render_template('email/dashboard.html', 
                         email_lists=email_lists,
                         email_campaigns=email_campaigns)

@email_bp.route('/lists/create', methods=['GET', 'POST'])
@login_required
def create_list():
    """Créer une nouvelle liste email"""
    if request.method == 'POST':
        list_name = request.form.get('list_name')
        description = request.form.get('description', '')
        provider = request.form.get('provider', 'mailchimp')
        
        result = email_manager.create_email_list(list_name, description, provider)
        
        if result['success']:
            flash(f'Liste "{list_name}" créée avec succès', 'success')
            return redirect(url_for('email_marketing.dashboard'))
        else:
            flash(f'Erreur lors de la création: {result["error"]}', 'danger')
    
    return render_template('email/create_list.html')

@email_bp.route('/campaigns/create', methods=['GET', 'POST'])
@login_required
def create_campaign():
    """Créer une nouvelle campagne email"""
    if request.method == 'POST':
        campaign_name = request.form.get('campaign_name')
        subject = request.form.get('subject')
        content = request.form.get('content')
        list_id = request.form.get('list_id')
        provider = request.form.get('provider', 'mailchimp')
        
        result = email_manager.create_email_campaign(
            campaign_name, subject, content, list_id, current_user.id, provider
        )
        
        if result['success']:
            flash(f'Campagne "{campaign_name}" créée avec succès', 'success')
            return redirect(url_for('email_marketing.dashboard'))
        else:
            flash(f'Erreur lors de la création: {result["error"]}', 'danger')
    
    # Récupérer les listes disponibles
    email_lists = EmailList.query.filter_by(user_id=current_user.id).all()
    return render_template('email/create_campaign.html', email_lists=email_lists)

@email_bp.route('/campaigns/<campaign_id>/send', methods=['POST'])
@login_required
def send_campaign(campaign_id):
    """Envoyer une campagne email"""
    provider = request.form.get('provider', 'mailchimp')
    
    result = email_manager.send_campaign(campaign_id, provider)
    
    if result['success']:
        flash('Campagne envoyée avec succès', 'success')
    else:
        flash(f'Erreur lors de l\'envoi: {result["error"]}', 'danger')
    
    return redirect(url_for('email_marketing.dashboard'))

@email_bp.route('/api/campaign-stats/<campaign_id>')
@login_required
def get_campaign_stats(campaign_id):
    """API pour récupérer les stats d'une campagne"""
    provider = request.args.get('provider', 'mailchimp')
    
    stats = email_manager.get_campaign_stats(campaign_id, provider)
    return jsonify(stats)

@email_bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Endpoint public pour inscription aux newsletters"""
    email = request.form.get('email')
    first_name = request.form.get('first_name', '')
    last_name = request.form.get('last_name', '')
    list_id = request.form.get('list_id')
    provider = request.form.get('provider', 'mailchimp')
    
    if not email or not list_id:
        return jsonify({'success': False, 'error': 'Email et liste requis'}), 400
    
    result = email_manager.add_subscriber(email, first_name, last_name, list_id, provider)
    
    return jsonify(result), 200 if result['success'] else 400

def setup_email_marketing():
    """Configuration initiale de l'email marketing"""
    try:
        logger.info("Configuration email marketing initialisée")
        return True
    except Exception as e:
        logger.error(f"Erreur configuration email marketing: {e}")
        return False
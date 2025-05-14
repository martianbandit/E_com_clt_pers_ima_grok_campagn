import os
import json
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_babel import gettext as _
from i18n import babel, get_locale, get_supported_languages, get_language_name, get_boutique_languages, is_multilingual_campaign, get_campaign_target_languages

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if database_url is None:
    raise RuntimeError("DATABASE_URL environment variable is not set. PostgreSQL database is required.")
    
# Check if DATABASE_URL starts with postgres://, and if so, replace with postgresql://
# This is required for SQLAlchemy 1.4.x+
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
    
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
babel.init_app(app, locale_selector=get_locale)

# Import routes after app initialization
from models import Boutique, NicheMarket, Customer, Campaign, SimilarProduct, Metric, Product, ImportedProduct
import asyncio
import aliexpress_importer
import product_generator
from boutique_ai import (
    generate_customers, 
    generate_customer_persona, 
    generate_marketing_content,
    GROK_2_IMAGE,
    generate_marketing_image
)

# Ajouter des filtres Jinja personnalisés
@app.template_filter('nl2br')
def nl2br_filter(s):
    """Convertit les retours à la ligne en balises <br>"""
    if s is None:
        return ""
    return Markup(s.replace('\n', '<br>'))

# Function to log metrics to the database
def log_metric(metric_name, data, category=None, status=None, response_time=None, customer_id=None):
    """
    Fonction améliorée pour enregistrer des métriques dans la base de données
    
    Args:
        metric_name: Nom de la métrique
        data: Données à enregistrer (dictionnaire)
        category: Catégorie de la métrique (ai, user, system, etc.)
        status: État (success, error, warning, info)
        response_time: Temps de réponse en ms (pour les appels API)
        customer_id: ID du client associé (si pertinent)
    
    Returns:
        Métrique créée ou None en cas d'erreur
    """
    try:
        # Extraire automatiquement le statut des données si non spécifié
        if status is None and isinstance(data, dict) and 'success' in data:
            # Conversion explicite en booléen (True/False) au lieu de chaîne de caractères
            status = True if data['success'] else False
        elif status == 'success':
            # Convertir 'success' en True
            status = True
        elif status == 'error':
            # Convertir 'error' en False
            status = False
        
        # Extraire automatiquement la catégorie si non spécifiée
        if category is None:
            # Détection basée sur le nom de la métrique
            if 'ai_' in metric_name or 'grok_' in metric_name or 'openai_' in metric_name:
                category = 'ai'
            elif 'user_' in metric_name:
                category = 'user'
            elif 'system_' in metric_name:
                category = 'system'
            elif 'generation' in metric_name:
                category = 'generation'
            elif 'import' in metric_name:
                category = 'import'
            else:
                category = 'misc'
        
        # Créer et sauvegarder la métrique
        metric = Metric(
            name=metric_name,
            category=category,
            status=status,
            data=data,
            response_time=response_time,
            created_at=datetime.datetime.utcnow(),
            customer_id=customer_id
        )
        db.session.add(metric)
        db.session.commit()
        
        # Journal des métriques importantes ou des erreurs uniquement
        if status is False:
            logging.error(f"Metric Error: {metric_name} - {json.dumps(data)}")
        else:
            logging.info(f"Metric: {metric_name} ({category}) - Status: {status}")
            
        return metric
    except Exception as e:
        logging.error(f"Failed to log metric {metric_name}: {e}")
        db.session.rollback()
        return None

@app.route('/change_language/<string:lang>')
def change_language(lang):
    """Change the application language"""
    # Only accept valid languages from the supported list
    if lang not in get_supported_languages():
        lang = 'en'
    
    # Store the language in the session
    session['language'] = lang
    
    # Redirect back to the page they were on
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/boutique_language_settings/<int:boutique_id>', methods=['GET'])
def boutique_language_settings(boutique_id):
    """Affiche les paramètres linguistiques d'une boutique"""
    boutique = Boutique.query.get_or_404(boutique_id)
    supported_languages = get_supported_languages()
    
    return render_template('language_settings.html', 
                          boutique=boutique, 
                          supported_languages=supported_languages)

@app.route('/save_boutique_language_settings', methods=['POST'])
def save_boutique_language_settings():
    """Enregistre les paramètres linguistiques d'une boutique"""
    boutique_id = request.form.get('boutique_id', type=int)
    boutique = Boutique.query.get_or_404(boutique_id)
    
    # Récupérer les données du formulaire
    language = request.form.get('language', 'en')
    multilingual_enabled = request.form.get('multilingual_enabled') == 'on'
    supported_languages = request.form.getlist('supported_languages')
    
    # Vérifier que la langue principale est toujours dans les langues supportées
    if language not in supported_languages:
        supported_languages.append(language)
    
    # Mettre à jour la boutique
    boutique.language = language
    boutique.multilingual_enabled = multilingual_enabled
    boutique.supported_languages = supported_languages
    
    # Sauvegarder les changements
    db.session.commit()
    
    flash(_('Language settings updated successfully'), 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/campaign_language_settings/<int:campaign_id>', methods=['GET'])
def campaign_language_settings(campaign_id):
    """Affiche les paramètres linguistiques d'une campagne"""
    campaign = Campaign.query.get_or_404(campaign_id)
    supported_languages = get_supported_languages()
    
    return render_template('campaign_language_settings.html', 
                          campaign=campaign, 
                          supported_languages=supported_languages,
                          get_campaign_target_languages=get_campaign_target_languages)

@app.route('/save_campaign_language_settings', methods=['POST'])
def save_campaign_language_settings():
    """Enregistre les paramètres linguistiques d'une campagne"""
    campaign_id = request.form.get('campaign_id', type=int)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Récupérer les données du formulaire
    language = request.form.get('language', 'en')
    multilingual_campaign = request.form.get('multilingual_campaign') == 'on'
    target_languages = request.form.getlist('target_languages')
    
    # Vérifier que la langue principale est toujours dans les langues cibles
    if language not in target_languages:
        target_languages.append(language)
    
    # Mettre à jour la campagne
    campaign.language = language
    campaign.multilingual_campaign = multilingual_campaign
    campaign.target_languages = target_languages
    
    # Sauvegarder les changements
    db.session.commit()
    
    flash(_('Campaign language settings updated successfully'), 'success')
    
    return redirect(url_for('edit_campaign', campaign_id=campaign.id))

@app.route('/dashboard')
def dashboard():
    # Récupérer les données pour le tableau de bord
    boutiques = Boutique.query.all()
    niches = NicheMarket.query.all()
    
    # Récupérer les métriques pour les analyses
    persona_metrics = Metric.query.filter_by(name='persona_generation').order_by(Metric.created_at.desc()).limit(10).all()
    profile_metrics = Metric.query.filter_by(name='profile_generation').order_by(Metric.created_at.desc()).limit(10).all()
    
    # Compter le nombre total d'éléments
    total_customers = Customer.query.count()
    total_campaigns = Campaign.query.count()
    total_boutiques = len(boutiques)
    total_niches = len(niches)
    
    # Récupérer les dernières campagnes créées
    recent_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          boutiques=boutiques, 
                          niches=niches,
                          persona_metrics=persona_metrics,
                          profile_metrics=profile_metrics,
                          total_customers=total_customers,
                          total_campaigns=total_campaigns,
                          total_boutiques=total_boutiques,
                          total_niches=total_niches,
                          recent_campaigns=recent_campaigns)

@app.route('/metrics')
def metrics():
    """Page d'affichage et d'analyse des métriques"""
    # Récupérer les paramètres de filtre de l'URL
    category = request.args.get('category')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    
    # Convertir les dates si présentes
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            flash(_('Format de date de début invalide. Utilisation du format par défaut.'), 'warning')
    
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            # Ajouter un jour pour inclure toute la journée
            end_date = end_date + datetime.timedelta(days=1)
        except ValueError:
            flash(_('Format de date de fin invalide. Utilisation du format par défaut.'), 'warning')
    
    # Récupérer le résumé des métriques
    metrics_summary = Metric.get_metrics_summary(
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    # Statistiques par catégorie
    category_stats = {}
    if category:
        # Si une catégorie est sélectionnée, calculer les sous-catégories (par nom)
        metrics_by_name = db.session.query(
            Metric.name, 
            db.func.count(Metric.id).label('count')
        ).filter(Metric.category == category).group_by(Metric.name).all()
        
        for name, count in metrics_by_name:
            category_stats[name] = count
    else:
        # Sinon, calculer les statistiques par catégorie principale
        metrics_by_category = db.session.query(
            Metric.category, 
            db.func.count(Metric.id).label('count')
        ).group_by(Metric.category).all()
        
        for cat, count in metrics_by_category:
            if cat:  # Éviter les catégories None
                category_stats[cat] = count
            else:
                category_stats['Non catégorisé'] = count
    
    # Données pour la série temporelle
    time_series_data = []
    
    # Déterminer l'intervalle de temps approprié (jour, semaine, mois)
    if start_date and end_date:
        delta = end_date - start_date
        if delta.days > 60:  # Plus de 2 mois
            interval = 'month'
        elif delta.days > 14:  # Plus de 2 semaines
            interval = 'week'
        else:
            interval = 'day'
    else:
        # Par défaut, utiliser les 30 derniers jours avec intervalle quotidien
        interval = 'day'
        if not start_date:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        if not end_date:
            end_date = datetime.datetime.utcnow()
    
    # Générer la série temporelle
    current_date = start_date
    while current_date <= end_date:
        if interval == 'day':
            next_date = current_date + datetime.timedelta(days=1)
            date_format = '%d/%m/%Y'
        elif interval == 'week':
            next_date = current_date + datetime.timedelta(days=7)
            date_format = '%d/%m/%Y'
        else:  # month
            if current_date.month == 12:
                next_date = datetime.datetime(current_date.year + 1, 1, 1)
            else:
                next_date = datetime.datetime(current_date.year, current_date.month + 1, 1)
            date_format = '%m/%Y'
        
        # Compter les métriques dans l'intervalle
        success_count = Metric.query.filter(
            Metric.created_at >= current_date,
            Metric.created_at < next_date,
            Metric.status == True
        ).count()
        
        error_count = Metric.query.filter(
            Metric.created_at >= current_date,
            Metric.created_at < next_date,
            Metric.status == False
        ).count()
        
        time_series_data.append({
            'date': current_date.strftime(date_format),
            'success_count': success_count,
            'error_count': error_count,
            'total': success_count + error_count
        })
        
        current_date = next_date
    
    return render_template('metrics.html',
                           metrics_summary=metrics_summary,
                           category_stats=category_stats,
                           time_series_data=time_series_data,
                           selected_category=category,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           limit=limit)

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    if request.method == 'POST':
        niche_id = int(request.form.get('niche_id', 0))
        num_profiles = int(request.form.get('num_profiles', 5))
        persist_to_db = request.form.get('persist_to_db') == 'on'
        
        # Nouveaux paramètres
        target_country = request.form.get('target_country', '')
        age_range = request.form.get('age_range', '')
        income_level = request.form.get('income_level', '')
        
        try:
            # Generate customer profiles for the selected niche
            niche = NicheMarket.query.get(niche_id)
            if niche:
                # Generate profiles with AI with additional parameters
                generation_params = {
                    'target_country': target_country,
                    'age_range': age_range,
                    'income_level': income_level
                }
                
                customer_profiles = generate_customers(niche.name, niche.description, num_profiles, generation_params)
                
                # Log metric for profile generation
                log_metric("profile_generation", {
                    "success": True,
                    "niche_id": niche_id,
                    "niche_name": niche.name,
                    "count": len(customer_profiles),
                    "persist_to_db": persist_to_db,
                    "target_country": target_country,
                    "age_range": age_range,
                    "income_level": income_level
                })
                
                # Store profiles in the session
                session['customer_profiles'] = customer_profiles
                
                # If requested, persist profiles to the database
                if persist_to_db:
                    saved_profiles = 0
                    for profile_dict in customer_profiles:
                        # Create Customer objects and save to database
                        customer = Customer.from_profile_dict(profile_dict, niche_id)
                        db.session.add(customer)
                        saved_profiles += 1
                    
                    db.session.commit()
                    flash(f'Successfully generated and saved {saved_profiles} customer profiles', 'success')
                else:
                    flash('Successfully generated customer profiles (not saved to database)', 'success')
            else:
                flash('Invalid niche selected', 'danger')
                log_metric("profile_generation", {
                    "success": False,
                    "error": "Invalid niche selected",
                    "niche_id": niche_id
                })
        except Exception as e:
            flash(f'Error generating profiles: {str(e)}', 'danger')
            logging.error(f"Error generating profiles: {e}")
            log_metric("profile_generation", {
                "success": False,
                "error": str(e),
                "niche_id": niche_id
            })
        
        return redirect(url_for('profiles'))
    
    # Get data for the page
    niches = NicheMarket.query.all()
    customer_profiles = session.get('customer_profiles', [])
    
    # Get saved profiles from database for display
    saved_profiles = Customer.query.order_by(Customer.created_at.desc()).limit(20).all()
    
    return render_template('profiles.html', 
                           niches=niches, 
                           profiles=customer_profiles,
                           saved_profiles=saved_profiles)

@app.route('/generate_persona/<int:profile_index>', methods=['POST'])
def generate_persona(profile_index):
    customer_profiles = session.get('customer_profiles', [])
    
    if not customer_profiles or profile_index >= len(customer_profiles):
        return jsonify({'error': 'Invalid profile'}), 400
    
    try:
        profile = customer_profiles[profile_index]
        persona = generate_customer_persona(profile)
        
        # Update the profile with the persona
        customer_profiles[profile_index]['persona'] = persona
        session['customer_profiles'] = customer_profiles
        
        # Log metric for persona generation
        log_metric("persona_generation", {
            "success": True,
            "profile_name": profile.get('name', 'Unknown'),
            "niche": profile.get('interests', ['Unknown'])[0] if profile.get('interests') else 'Unknown'
        })
        
        return jsonify({'success': True, 'persona': persona})
    except Exception as e:
        # Log metric for failed persona generation
        log_metric("persona_generation", {
            "success": False,
            "error": str(e)
        })
        
        logging.error(f"Error generating persona: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/campaigns', methods=['GET', 'POST'])
def campaigns():
    if request.method == 'POST':
        profile_source = request.form.get('profile_source', 'session')
        campaign_type = request.form.get('campaign_type', 'email')
        
        # Obtenir le profil soit de la session, soit de la base de données
        profile = None
        if profile_source == 'session':
            profile_index = int(request.form.get('profile_index', 0))
            customer_profiles = session.get('customer_profiles', [])
            
            if not customer_profiles or profile_index >= len(customer_profiles):
                flash('Invalid profile selected', 'danger')
                return redirect(url_for('campaigns'))
            
            profile = customer_profiles[profile_index]
            customer_id = None
        else:
            # Profil de la base de données
            customer_id = int(request.form.get('customer_id', 0))
            customer = Customer.query.get(customer_id)
            
            if not customer:
                flash('Invalid customer selected', 'danger')
                return redirect(url_for('campaigns'))
            
            # Utiliser les données de profil stockées ou convertir l'objet en dictionnaire
            profile = customer.profile_data if customer.profile_data else {
                'name': customer.name,
                'age': customer.age,
                'location': customer.location,
                'gender': customer.gender,
                'language': customer.language,
                'interests': customer.get_interests_list(),
                'preferred_device': customer.preferred_device,
                'persona': customer.persona
            }
        
        try:
            # Générer le contenu marketing personnalisé
            content = generate_marketing_content(profile, campaign_type)
            
            # Log metric pour la génération de contenu marketing
            log_metric("marketing_content_generation", {
                "success": True,
                "profile_name": profile.get('name', 'Unknown'),
                "campaign_type": campaign_type
            })
            
            # Générer une image pour la campagne si demandé
            image_prompt = request.form.get('image_prompt', '')
            image_url = None
            if image_prompt:
                image_url = generate_marketing_image(profile, image_prompt)
                
                # Log metric pour la génération d'image
                log_metric("marketing_image_generation", {
                    "success": True if image_url else False,
                    "prompt": image_prompt
                })
            
            # Créer et sauvegarder la campagne
            campaign = Campaign(
                title=request.form.get('title', f"Campaign for {profile.get('name', 'Customer')}"),
                content=content,
                campaign_type=campaign_type,
                profile_data=profile,
                image_url=image_url,
                customer_id=customer_id
            )
            db.session.add(campaign)
            db.session.commit()
            
            flash('Campaign created successfully', 'success')
            
            # Rediriger vers la page de détail de la campagne
            return redirect(url_for('view_campaign', campaign_id=campaign.id))
        except Exception as e:
            flash(f'Error creating campaign: {str(e)}', 'danger')
            logging.error(f"Error creating campaign: {e}")
            
            # Log metric pour l'échec de génération
            log_metric("marketing_content_generation", {
                "success": False,
                "error": str(e),
                "campaign_type": campaign_type
            })
        
        return redirect(url_for('campaigns'))
    
    # GET request - afficher la page des campagnes
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    customer_profiles = session.get('customer_profiles', [])
    
    # Récupérer les clients sauvegardés pour la sélection
    saved_customers = Customer.query.order_by(Customer.name).all()
    
    return render_template('campaigns.html', 
                          campaigns=campaigns, 
                          profiles=customer_profiles,
                          saved_customers=saved_customers)

@app.route('/api/boutiques', methods=['POST'])
def create_boutique():
    data = request.json
    try:
        boutique = Boutique(
            name=data.get('name'),
            description=data.get('description'),
            target_demographic=data.get('target_demographic')
        )
        db.session.add(boutique)
        db.session.commit()
        return jsonify({'id': boutique.id, 'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/niches', methods=['POST'])
def create_niche():
    data = request.json
    try:
        niche = NicheMarket(
            name=data.get('name'),
            description=data.get('description'),
            key_characteristics=data.get('key_characteristics')
        )
        db.session.add(niche)
        db.session.commit()
        return jsonify({'id': niche.id, 'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/niches/<int:niche_id>', methods=['PUT'])
def edit_niche(niche_id):
    """Modifier une niche de marché via API"""
    data = request.json
    niche = NicheMarket.query.get_or_404(niche_id)
    
    try:
        if data.get('name'):
            niche.name = data.get('name')
        if data.get('description') is not None:
            niche.description = data.get('description')
        if data.get('key_characteristics') is not None:
            niche.key_characteristics = data.get('key_characteristics')
        
        niche.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'id': niche.id, 
            'name': niche.name,
            'status': 'success'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/niches/<int:niche_id>', methods=['DELETE'])
def delete_niche(niche_id):
    """Supprimer une niche de marché via API"""
    niche = NicheMarket.query.get_or_404(niche_id)
    
    try:
        # Vérifier s'il y a des clients associés
        customers_count = Customer.query.filter_by(niche_market_id=niche_id).count()
        
        if customers_count > 0:
            return jsonify({
                'error': f'Cannot delete niche: {customers_count} customer(s) are associated with it.',
                'status': 'error'
            }), 400
        
        db.session.delete(niche)
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error'}), 400

@app.route('/customer/<int:customer_id>')
def view_customer(customer_id):
    """Afficher les détails d'un client spécifique"""
    customer = Customer.query.get_or_404(customer_id)
    return render_template('customer_detail.html', customer=customer)

@app.route('/customer/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Modifier les informations d'un client"""
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs du client
            customer.name = request.form.get('name', customer.name)
            customer.age = request.form.get('age', customer.age)
            customer.location = request.form.get('location', customer.location)
            customer.country_code = request.form.get('country_code', customer.country_code)
            customer.gender = request.form.get('gender', customer.gender)
            customer.language = request.form.get('language', customer.language)
            customer.interests = request.form.get('interests', customer.interests)
            customer.preferred_device = request.form.get('preferred_device', customer.preferred_device)
            customer.persona = request.form.get('persona', customer.persona)
            
            # Nouveaux champs
            customer.occupation = request.form.get('occupation', customer.occupation)
            customer.education = request.form.get('education', customer.education)
            customer.income_level = request.form.get('income_level', customer.income_level)
            customer.shopping_frequency = request.form.get('shopping_frequency', customer.shopping_frequency)
            
            # Niche de marché
            niche_market_id = request.form.get('niche_market_id')
            if niche_market_id:
                customer.niche_market_id = int(niche_market_id)
            else:
                customer.niche_market_id = None
            
            # Si des données JSON sont soumises, les traiter
            profile_data = request.form.get('profile_data')
            if profile_data:
                try:
                    customer.profile_data = json.loads(profile_data)
                except json.JSONDecodeError:
                    flash('Invalid JSON format for profile data', 'danger')
            
            db.session.commit()
            flash('Customer updated successfully', 'success')
            return redirect(url_for('view_customer', customer_id=customer.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
    
    # GET request - afficher le formulaire de modification
    niches = NicheMarket.query.all()
    return render_template('customer_edit.html', customer=customer, niches=niches)

@app.route('/customer/<int:customer_id>/delete', methods=['GET', 'POST'])
def delete_customer(customer_id):
    """Supprimer un client"""
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Client supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du client: {str(e)}', 'danger')
    return redirect(url_for('profiles'))

@app.route('/generate_customer_persona/<int:customer_id>', methods=['POST'])
def generate_customer_persona_db(customer_id):
    """Générer un persona pour un client dans la base de données"""
    from boutique_ai import generate_enhanced_customer_data_async, AsyncOpenAI, grok_client
    import asyncio
    import traceback
    import persona_manager  # Importer le module de gestion des personas
    from models import CustomerPersona, CustomerPersonaAssociation
    
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        # Incrémenter le compteur d'utilisation du profil
        customer.usage_count = (customer.usage_count or 0) + 1
        
        # Préparer les données du profil pour la génération
        profile = customer.profile_data if customer.profile_data else {
            'name': customer.name,
            'age': customer.age,
            'location': customer.location,
            'gender': customer.gender,
            'language': customer.language,
            'interests': customer.get_interests_list(),
            'preferred_device': customer.preferred_device,
            'id': customer.id  # Ajouter l'ID pour permettre les mises à jour des attributs supplémentaires
        }
        
        # Récupérer le nom de la niche associée au client
        niche_name = "general boutique"
        if customer.niche_market:
            niche_name = customer.niche_market.name
        
        # Récupérer les personas existants pour éviter la répétition
        existing_personas = []
        other_customers = Customer.query.filter(Customer.id != customer_id, Customer.persona != None).order_by(Customer.created_at.desc()).limit(5).all()
        for other in other_customers:
            if other.persona:
                existing_personas.append(other.persona)
        
        # Utiliser asyncio pour exécuter la génération asynchrone
        async def generate_data():
            return await generate_enhanced_customer_data_async(
                client=grok_client,
                customer=profile,
                niche=niche_name,
                existing_personas=existing_personas,
                boutique_info=None if not customer.boutique_id else {
                    "name": customer.boutique.name if customer.boutique else "",
                    "description": customer.boutique.description if customer.boutique else "",
                    "target_demographic": customer.boutique.target_demographic if customer.boutique else ""
                }
            )
        
        # Exécuter la fonction asynchrone
        enhanced_data = asyncio.run(generate_data())
        
        # Mettre à jour le client avec les nouvelles données enrichies
        customer.persona = enhanced_data["persona"]
        customer.niche_attributes = enhanced_data["niche_attributes"]
        customer.purchased_products = enhanced_data["purchased_products"]
        
        # Pour l'avatar, nous allons générer l'image avec le prompt fourni
        # Mais comme la génération d'image prend du temps, nous allons d'abord stocker le prompt
        customer.avatar_prompt = enhanced_data["avatar_prompt"]
        
        db.session.commit()
        
        # Créer un persona structuré et l'associer au client
        try:
            # Vérifier si un persona principal existe déjà pour ce client
            existing_primary = CustomerPersonaAssociation.query.filter_by(
                customer_id=customer.id,
                is_primary=True
            ).first()
            
            # Si un persona principal existe déjà, le mettre à jour
            if existing_primary:
                persona = existing_primary.persona
                # Mettre à jour les champs du persona
                persona.description = enhanced_data["persona"]
                persona.niche_specific_attributes = enhanced_data["niche_attributes"]
                persona.avatar_prompt = enhanced_data["avatar_prompt"]
                
                # Extraire les valeurs spécifiques des attributs de niche si disponibles
                if customer.niche_attributes and isinstance(customer.niche_attributes, dict):
                    for key, value in customer.niche_attributes.items():
                        if key == "interests" and value:
                            persona.interests = value
                        elif key == "values" and value:
                            persona.values = value
                        elif key == "preferred_channels" and value:
                            persona.preferred_channels = value
                
                db.session.commit()
                logging.info(f"Persona existant mis à jour pour le client {customer.id}: {persona.id}")
                persona_id = persona.id
            else:
                # Créer un nouveau persona
                persona_title = f"Persona pour {customer.name}"
                
                # Extraire les attributs spécifiques pour le persona
                additional_data = {
                    'primary_goal': None,  # À compléter ultérieurement
                    'pain_points': None,  # À compléter ultérieurement
                    'age_range': f"{customer.age - 5}-{customer.age + 5}" if customer.age else None,
                    'gender_affinity': customer.gender,
                    'location_type': "Urbain" if customer.location and any(city in customer.location.lower() for city in ["paris", "lyon", "marseille", "lille", "bordeaux"]) else "Périurbain",
                    'income_bracket': customer.income_level,
                    'education_level': customer.education,
                    'niche_specific_attributes': enhanced_data["niche_attributes"],
                    'avatar_prompt': enhanced_data["avatar_prompt"]
                }
                
                # Créer le persona
                new_persona = persona_manager.create_persona_from_text(
                    title=persona_title,
                    description=enhanced_data["persona"],
                    niche_market_id=customer.niche_market_id,
                    boutique_id=customer.boutique_id,
                    additional_data=additional_data
                )
                
                # Assigner le persona au client
                assoc = persona_manager.assign_persona_to_customer(
                    customer_id=customer.id,
                    persona_id=new_persona.id,
                    is_primary=True,
                    relevance_score=1.0,
                    notes="Persona généré automatiquement"
                )
                
                logging.info(f"Nouveau persona créé et assigné au client {customer.id}: {new_persona.id}")
                persona_id = new_persona.id
        except Exception as persona_error:
            logging.error(f"Erreur lors de la création du persona structuré: {persona_error}\n{traceback.format_exc()}")
            # Ne pas échouer toute la requête si cette partie échoue
        
        # Log metric pour la génération de persona
        log_metric("persona_generation", {
            "success": True,
            "customer_id": customer.id,
            "profile_name": customer.name,
            "enhanced": True,
            "avatar_prompt_generated": True
        })
        
        return jsonify({
            'success': True, 
            'persona': enhanced_data["persona"],
            'niche_attributes': enhanced_data["niche_attributes"],
            'purchased_products': enhanced_data["purchased_products"],
            'avatar_prompt': enhanced_data["avatar_prompt"]
        })
    except Exception as e:
        db.session.rollback()
        # Log metric pour l'échec de génération
        log_metric("persona_generation", {
            "success": False,
            "customer_id": customer.id,
            "error": str(e)
        })
        
        logging.error(f"Error generating enhanced persona for customer {customer_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>')
def view_campaign(campaign_id):
    """Afficher les détails d'une campagne spécifique"""
    campaign = Campaign.query.get_or_404(campaign_id)
    return render_template('campaign_detail.html', campaign=campaign)

@app.route('/campaign/<int:campaign_id>/generate-image', methods=['GET', 'POST'])
def generate_campaign_image(campaign_id):
    """Générer ou régénérer une image pour une campagne spécifique"""
    campaign = Campaign.query.get_or_404(campaign_id)
    
    try:
        # Récupérer le profil client associé
        customer = campaign.customer
        
        # Créer un profil, même générique si pas de client
        if customer:
            profile = {
                "name": customer.name,
                "age": customer.age,
                "location": customer.location,
                "language": customer.language,
                "interests": customer.get_interests_list() if hasattr(customer, 'get_interests_list') else customer.interests,
                "occupation": customer.occupation if hasattr(customer, 'occupation') else "Non spécifié",
                "avatar_url": customer.avatar_url
            }
        else:
            # Créer un profil générique pour les campagnes sans client
            profile = {
                "name": "Utilisateur",
                "age": 30,
                "location": "France",
                "language": "fr",
                "interests": [campaign.campaign_type or "marketing"],
                "occupation": "Client potentiel",
                "avatar_url": None
            }
        
        # Générer un prompt si aucun n'est déjà défini
        image_prompt = campaign.image_prompt
        if not image_prompt:
            # Générer un prompt à partir du contenu de la campagne et du profil client
            from boutique_ai import generate_image_prompt_from_content
            image_prompt = generate_image_prompt_from_content(
                campaign_content=campaign.content,
                campaign_type=campaign.campaign_type,
                customer_profile=profile
            )
        
        # Générer l'image
        image_url = generate_marketing_image(profile, image_prompt)
        
        # Mettre à jour la campagne
        campaign.image_url = image_url
        campaign.image_prompt = image_prompt
        db.session.commit()
        
        # Journal des métriques
        log_metric(
            metric_name="campaign_image_generation",
            data={
                "campaign_id": campaign.id,
                "prompt": image_prompt
            },
            category="generation",
            status=True
        )
        
        flash(_("Image de campagne générée avec succès"), 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Erreur lors de la génération de l'image de campagne: {e}")
        flash(_("Erreur lors de la génération de l'image: {}").format(str(e)), 'danger')
    
    return redirect(url_for('view_campaign', campaign_id=campaign_id))

@app.route('/campaign/<int:campaign_id>/delete', methods=['GET', 'POST'])
def delete_campaign(campaign_id):
    """Supprimer une campagne"""
    campaign = Campaign.query.get_or_404(campaign_id)
    try:
        db.session.delete(campaign)
        db.session.commit()
        flash('Campagne supprimée avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression de la campagne: {str(e)}', 'danger')
    return redirect(url_for('campaigns'))

@app.route('/generate_customer_avatar/<int:customer_id>', methods=['POST'])
def generate_customer_avatar(customer_id):
    """Générer un avatar pour un client basé sur son persona et ses attributs"""
    from boutique_ai import generate_boutique_image_async, AsyncOpenAI, grok_client, GROK_2_IMAGE
    import asyncio
    
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        # Incrémenter le compteur d'utilisation du profil
        customer.usage_count = (customer.usage_count or 0) + 1
        
        # Vérifier si le client a un avatar_prompt
        if not customer.avatar_prompt:
            return jsonify({
                'error': 'Ce client n\'a pas de prompt d\'avatar. Veuillez d\'abord générer un persona.'
            }), 400
        
        # Utiliser asyncio pour exécuter la génération d'image asynchrone
        async def generate_avatar():
            # Ajouter les informations de la boutique au prompt
            boutique_info = None
            if customer.boutique_id:
                try:
                    boutique = customer.boutique
                    if boutique:
                        boutique_info = {
                            "name": boutique.name,
                            "description": boutique.description,
                            "target_demographic": boutique.target_demographic
                        }
                        # Enrichir le prompt avec des informations de la boutique
                        enhanced_prompt = f"{customer.avatar_prompt} This avatar should reflect the style and aesthetic of '{boutique.name}' boutique, which is {boutique.description}."
                    else:
                        enhanced_prompt = customer.avatar_prompt
                except Exception as e:
                    logging.warning(f"Could not retrieve boutique information: {e}")
                    enhanced_prompt = customer.avatar_prompt
            else:
                enhanced_prompt = customer.avatar_prompt
                
            # Générer l'image avec les informations de contexte enrichies
            try:
                avatar_url = await generate_boutique_image_async(
                    client=grok_client,
                    image_prompt=enhanced_prompt,
                    model=GROK_2_IMAGE
                )
                # Vérifier si c'est une URL d'erreur (placeholder)
                if avatar_url.startswith("https://placehold.co") or "Error" in avatar_url:
                    raise Exception("L'image n'a pas pu être générée correctement. Le service d'IA a retourné une erreur.")
                return avatar_url
            except Exception as img_error:
                logging.error(f"Error in avatar generation API call: {img_error}")
                error_details = str(img_error)
                if "400" in error_details or "invalid_request_error" in error_details:
                    raise Exception("Le contenu du prompt n'est pas accepté par l'API image. Veuillez régénérer le persona.")
                elif "429" in error_details or "rate limit" in error_details.lower():
                    raise Exception("Limite de requêtes atteinte. Veuillez réessayer dans quelques minutes.")
                else:
                    raise Exception(f"Erreur lors de la génération de l'avatar: {error_details}")
        
        # Exécuter la fonction asynchrone
        avatar_url = asyncio.run(generate_avatar())
        
        # Mettre à jour le client avec l'URL de l'avatar
        customer.avatar_url = avatar_url
        db.session.commit()
        
        # Log metric pour la génération d'avatar
        log_metric("avatar_generation", {
            "success": True,
            "customer_id": customer.id,
            "profile_name": customer.name
        })
        
        return jsonify({
            'success': True, 
            'avatar_url': avatar_url
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        # Log metric pour l'échec de génération
        log_metric("avatar_generation", {
            "success": False,
            "customer_id": customer.id,
            "profile_name": customer.name,
            "error": error_msg,
            "stack_trace": stack_trace[:500]  # Tronquer pour éviter les entrées trop longues
        }, category="generation", status=False)
    
        logging.error(f"Error generating avatar for customer {customer_id}: {e}\n{stack_trace}")
        
        # Formater un message d'erreur plus convivial
        user_friendly_error = error_msg
        if "API key" in error_msg.lower() or "openai" in error_msg.lower():
            user_friendly_error = "Problème de connexion avec le service d'IA. Veuillez vérifier les clés API."
        elif "timeout" in error_msg.lower():
            user_friendly_error = "Le délai d'attente a été dépassé. Veuillez réessayer."
        elif "exceeded" in error_msg.lower() or "quota" in error_msg.lower():
            user_friendly_error = "Quota d'utilisation dépassé. Veuillez réessayer plus tard."
        
        return jsonify({
            'success': False,
            'error': user_friendly_error,
            'details': error_msg
        }), 500

@app.route('/image_generation', methods=['GET', 'POST'])
def image_generation():
    """Page de génération d'images marketing optimisées avec recherche de produits similaires"""
    # Récupérer les clients sauvegardés pour la sélection
    saved_customers = Customer.query.order_by(Customer.name).all()
    
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id')
            base_prompt = request.form.get('base_prompt', '')
            style = request.form.get('style', None)
            find_similar = request.form.get('find_similar_products') == 'on'
            image_data = None
            
            # Vérifier si une image a été téléchargée
            if 'reference_image' in request.files and request.files['reference_image'].filename:
                import base64
                from io import BytesIO
                
                # Lire le fichier image
                uploaded_file = request.files['reference_image']
                image_bytes = BytesIO(uploaded_file.read())
                
                # Encoder en base64
                image_data = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
            
            # Récupérer le profil client
            customer = Customer.query.get(customer_id)
            if not customer:
                flash('Client invalide sélectionné', 'danger')
                return redirect(url_for('image_generation'))
                
            # Incrémenter le compteur d'utilisation du profil
            customer.usage_count = (customer.usage_count or 0) + 1
            
            # Convertir le client en dictionnaire pour l'API
            profile = customer.profile_data if customer.profile_data else {
                'name': customer.name,
                'age': customer.age,
                'location': customer.location,
                'gender': customer.gender,
                'language': customer.language,
                'interests': customer.get_interests_list(),
                'preferred_device': customer.preferred_device,
                'persona': customer.persona
            }
            
            # Récupérer les métadonnées SEO fournies par l'utilisateur
            user_seo_keywords = request.form.get('seo_keywords', '')
            user_seo_alt_text = request.form.get('seo_alt_text', '')
            user_seo_title = request.form.get('seo_title', '')
            
            # Générer l'image et les métadonnées SEO
            image_result = generate_marketing_image(
                profile, 
                base_prompt, 
                image_data=image_data, 
                style=style,
                boutique_id=customer.boutique_id if customer.boutique_id else None
            )
            
            # Déterminer si nous avons reçu une simple URL ou un dictionnaire complet
            if isinstance(image_result, dict) and "url" in image_result:
                image_url = image_result["url"]
                # Combiner les métadonnées générées par l'IA avec celles de l'utilisateur
                seo_metadata = {
                    "alt_text": user_seo_alt_text or image_result.get("alt_text", ""),
                    "title": user_seo_title or image_result.get("title", ""),
                    "description": image_result.get("description", ""),
                    "keywords": [],
                    "prompt": image_result.get("prompt", base_prompt)
                }
                
                # Traiter les mots-clés (priorité à l'utilisateur, puis l'IA)
                if user_seo_keywords:
                    seo_metadata["keywords"] = [k.strip() for k in user_seo_keywords.split(',') if k.strip()]
                elif "keywords" in image_result and image_result["keywords"]:
                    seo_metadata["keywords"] = image_result["keywords"]
            else:
                # Compatible avec l'ancienne version qui retourne juste l'URL
                image_url = image_result
                
                # Extraire les mots-clés des intérêts du client si l'utilisateur n'en a pas fourni
                keywords = []
                if user_seo_keywords:
                    keywords = [k.strip() for k in user_seo_keywords.split(',') if k.strip()]
                else:
                    keywords = customer.get_interests_list()
                    if not keywords and customer.niche_market:
                        keywords = [customer.niche_market.name]
                
                # Combiner les métadonnées par défaut avec celles de l'utilisateur
                default_alt_text = f"Image marketing pour {customer.name} dans la niche {', '.join(keywords[:2]) if keywords else 'boutique'}"
                default_title = request.form.get('title', f"Image marketing pour {customer.name}")
                
                seo_metadata = {
                    "alt_text": user_seo_alt_text or default_alt_text,
                    "title": user_seo_title or default_title,
                    "description": f"Image générée avec le prompt: {base_prompt}",
                    "keywords": keywords,
                    "prompt": base_prompt
                }
            
            # Créer et sauvegarder la campagne avec l'image et les métadonnées SEO
            campaign = Campaign(
                title=request.form.get('title', f"Image marketing pour {customer.name}"),
                content=f"Image générée avec le prompt: {base_prompt}",
                campaign_type="image",
                profile_data=profile,
                image_url=image_url,
                image_alt_text=seo_metadata["alt_text"],
                image_title=seo_metadata["title"],
                image_description=seo_metadata["description"],
                image_keywords=seo_metadata["keywords"],
                image_prompt=seo_metadata["prompt"],
                customer_id=customer_id
            )
            db.session.add(campaign)
            db.session.commit()
            
            # Rechercher des produits similaires sur AliExpress si demandé
            similar_products = []
            if find_similar:
                try:
                    # Importer le module de recherche AliExpress
                    from aliexpress_search import search_similar_products
                    
                    # Extraire les intérêts du client comme niche
                    niche = ""
                    if customer.interests:
                        niche = customer.get_interests_list()[0]
                    
                    # Rechercher des produits similaires
                    similar_products = search_similar_products(
                        base_prompt, 
                        campaign.id,
                        niche=niche, 
                        max_results=3
                    )
                    
                    if similar_products:
                        flash(f'{len(similar_products)} produits similaires trouvés sur AliExpress', 'success')
                except Exception as e:
                    logging.error(f"Error searching similar products: {e}")
                    flash('Erreur lors de la recherche de produits similaires', 'warning')
            
            # Log metric pour la génération d'image
            log_metric("marketing_image_generation", {
                "success": True if image_url else False,
                "prompt": base_prompt,
                "customer_id": customer_id,
                "style": style,
                "similar_products_found": len(similar_products) if similar_products else 0
            })
            
            flash('Image marketing générée avec succès', 'success')
            return redirect(url_for('view_campaign', campaign_id=campaign.id))
            
        except Exception as e:
            flash(f'Erreur lors de la génération de l\'image: {str(e)}', 'danger')
            logging.error(f"Error generating marketing image: {e}")
            
            # Log metric pour l'échec de génération
            log_metric("marketing_image_generation", {
                "success": False,
                "error": str(e)
            })
    
    # Styles disponibles pour la génération d'images
    available_styles = [
        {"id": "watercolor", "name": "Aquarelle"},
        {"id": "oil_painting", "name": "Peinture à l'huile"},
        {"id": "photorealistic", "name": "Photoréaliste"},
        {"id": "sketch", "name": "Croquis"},
        {"id": "anime", "name": "Anime"},
        {"id": "3d_render", "name": "Rendu 3D"},
        {"id": "minimalist", "name": "Minimaliste"},
        {"id": "pop_art", "name": "Pop Art"}
    ]
    
    return render_template('image_generation.html',
                          saved_customers=saved_customers,
                          available_styles=available_styles)

@app.route('/metrics')
def metrics_view():
    """Afficher les métriques de l'application"""
    # Récupérer les dernières métriques
    recent_metrics = Metric.query.order_by(Metric.created_at.desc()).limit(50).all()
    
    # Compter les métriques par type
    profile_gen_count = Metric.query.filter_by(name='profile_generation').count()
    persona_gen_count = Metric.query.filter_by(name='persona_generation').count()
    
    # Calculer les taux de succès
    successful_profiles = Metric.query.filter_by(name='profile_generation').filter(
        Metric.data.contains({'success': True})
    ).count()
    
    successful_personas = Metric.query.filter_by(name='persona_generation').filter(
        Metric.data.contains({'success': True})
    ).count()
    
    profile_success_rate = (successful_profiles / profile_gen_count * 100) if profile_gen_count > 0 else 0
    persona_success_rate = (successful_personas / persona_gen_count * 100) if persona_gen_count > 0 else 0
    
    return render_template('metrics.html', 
                           metrics=recent_metrics,
                           profile_gen_count=profile_gen_count,
                           persona_gen_count=persona_gen_count,
                           profile_success_rate=profile_success_rate,
                           persona_success_rate=persona_success_rate)

# Routes pour la gestion des produits
@app.route('/products', methods=['GET'])
def products():
    """Page de gestion des produits et génération de contenu"""
    # Récupérer les produits existants
    products_list = Product.query.order_by(Product.name).all()
    
    # Récupérer les clients pour le ciblage
    customers = Customer.query.order_by(Customer.name).all()
    
    # Récupérer les boutiques pour l'association des produits
    boutiques = Boutique.query.order_by(Boutique.name).all()
    
    return render_template('products.html',
                          products=products_list,
                          customers=customers,
                          boutiques=boutiques)

@app.route('/create_product', methods=['POST'])
def create_product():
    """Créer un nouveau produit"""
    try:
        # Créer le produit à partir des données du formulaire
        product = Product(
            name=request.form.get('name'),
            category=request.form.get('category'),
            price=float(request.form.get('price', 0)),
            base_description=request.form.get('base_description'),
            image_url=request.form.get('image_url')
        )
        
        # Associer à une boutique si spécifiée
        boutique_id = request.form.get('boutique_id')
        if boutique_id and boutique_id.isdigit():
            product.boutique_id = int(boutique_id)
        
        # Sauvegarder le produit
        db.session.add(product)
        db.session.commit()
        
        flash(f'Produit "{product.name}" créé avec succès', 'success')
        return redirect(url_for('view_product', product_id=product.id))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la création du produit: {str(e)}', 'danger')
        logging.error(f"Error creating product: {e}")
        return redirect(url_for('products'))

@app.route('/product/<int:product_id>', methods=['GET'])
def view_product(product_id):
    """Afficher les détails d'un produit spécifique"""
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """Modifier les informations d'un produit"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs du produit
            product.name = request.form.get('name', product.name)
            product.category = request.form.get('category')
            product.price = float(request.form.get('price', 0))
            product.base_description = request.form.get('base_description')
            product.image_url = request.form.get('image_url')
            
            # Associer à une boutique si spécifiée
            boutique_id = request.form.get('boutique_id')
            if boutique_id and boutique_id.isdigit():
                product.boutique_id = int(boutique_id)
            else:
                product.boutique_id = None
            
            # Associer à un public cible si spécifié
            target_audience_id = request.form.get('target_audience_id')
            if target_audience_id and target_audience_id.isdigit():
                product.target_audience_id = int(target_audience_id)
            else:
                product.target_audience_id = None
            
            # Mettre à jour les métadonnées SEO si fournies
            meta_title = request.form.get('meta_title')
            if meta_title:
                product.meta_title = meta_title
                
            meta_description = request.form.get('meta_description')
            if meta_description:
                product.meta_description = meta_description
                
            alt_text = request.form.get('alt_text')
            if alt_text:
                product.alt_text = alt_text
                
            keywords = request.form.get('keywords')
            if keywords:
                product.keywords = [k.strip() for k in keywords.split(',') if k.strip()]
            
            # Sauvegarder les modifications
            db.session.commit()
            
            flash(f'Produit "{product.name}" mis à jour avec succès', 'success')
            return redirect(url_for('view_product', product_id=product.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du produit: {str(e)}', 'danger')
            logging.error(f"Error updating product: {e}")
    
    # GET request - afficher le formulaire d'édition
    boutiques = Boutique.query.order_by(Boutique.name).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template('product_edit.html', 
                          product=product,
                          boutiques=boutiques,
                          customers=customers)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Supprimer un produit"""
    product = Product.query.get_or_404(product_id)
    
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'Produit "{product.name}" supprimé avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du produit: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

@app.route('/generate_product_content', methods=['POST'])
def generate_product_content():
    """Générer du contenu pour un produit (description, variantes, analyse comparative)"""
    try:
        product_id = request.form.get('product_id')
        product = Product.query.get_or_404(product_id)
        
        # Récupérer les options de génération
        generate_options = {
            "generate_description": request.form.get('generate_description') == '1',
            "generate_meta": request.form.get('generate_meta') == '1',
            "generate_variants": request.form.get('generate_variants') == '1',
            "generate_comparative": request.form.get('generate_comparative') == '1'
        }
        
        # Récupérer les instructions spécifiques
        instructions = request.form.get('generation_instructions', '')
        
        # Récupérer le public cible si spécifié
        target_audience = None
        target_audience_id = request.form.get('target_audience_id')
        if target_audience_id and target_audience_id.isdigit():
            customer = Customer.query.get(int(target_audience_id))
            if customer:
                target_audience = {
                    'name': customer.name,
                    'age': customer.age,
                    'location': customer.location,
                    'gender': customer.gender,
                    'interests': customer.get_interests_list(),
                    'persona': customer.persona
                }
                
                # Incrémenter le compteur d'utilisation du client
                customer.usage_count = (customer.usage_count or 0) + 1
                db.session.commit()
        
        # Préparation des données du produit
        product_data = {
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'price': product.price,
            'base_description': product.base_description
        }
        
        async def generate_content():
            try:
                # Générer le contenu principal
                content_result = await product_generator.generate_product_content(
                    product_data,
                    target_audience,
                    generate_options,
                    instructions
                )
                
                # Générer le HTML si demandé
                html_templates = None
                if request.form.get('generate_html') == '1':
                    html_templates = await product_generator.generate_product_html_templates(
                        {**product_data, **content_result},
                        "moyenne_gamme"  # Par défaut, ciblage moyen de gamme
                    )
                
                # Mettre à jour le produit avec le contenu généré
                if content_result:
                    if generate_options.get("generate_description"):
                        product.generated_title = content_result.get('generated_title')
                        product.generated_description = content_result.get('generated_description')
                    
                    if generate_options.get("generate_meta"):
                        product.meta_title = content_result.get('meta_title')
                        product.meta_description = content_result.get('meta_description')
                        product.alt_text = content_result.get('alt_text')
                        product.keywords = content_result.get('keywords')
                    
                    if generate_options.get("generate_variants"):
                        product.variants = content_result.get('variants')
                    
                    if generate_options.get("generate_comparative"):
                        product.comparative_analysis = content_result.get('comparative_analysis')
                
                # Ajouter le HTML généré si disponible
                if html_templates:
                    product.html_description = html_templates.get('html_description')
                    product.html_specifications = html_templates.get('html_specifications')
                    product.html_faq = html_templates.get('html_faq')
                
                # Si un client spécifique a été utilisé, mettre à jour la liaison
                if target_audience_id and target_audience_id.isdigit():
                    product.target_audience_id = int(target_audience_id)
                
                # Enregistrer les modifications
                db.session.commit()
            except Exception as e:
                logging.error(f"Error during async content generation: {e}")
                raise
        
        # Exécuter la génération en arrière-plan
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_content())
        loop.close()
        
        # Log metric pour la génération
        log_metric("product_content_generation", {
            "success": True,
            "product_id": product.id,
            "product_name": product.name,
            "options": generate_options
        })
        
        flash('Contenu généré avec succès!', 'success')
        return redirect(url_for('view_product', product_id=product.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la génération du contenu: {str(e)}', 'danger')
        logging.error(f"Error generating product content: {e}")
        
        # Log metric pour l'échec de génération
        log_metric("product_content_generation", {
            "success": False,
            "error": str(e)
        })
        
        return redirect(url_for('products'))

@app.route('/export_product/<int:product_id>', methods=['GET'])
def export_product(product_id):
    """Exporter un produit au format JSON"""
    product = Product.query.get_or_404(product_id)
    
    # Créer un dictionnaire avec toutes les données du produit
    product_data = {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'price': product.price,
        'base_description': product.base_description,
        'generated_title': product.generated_title,
        'generated_description': product.generated_description,
        'meta_title': product.meta_title,
        'meta_description': product.meta_description,
        'alt_text': product.alt_text,
        'keywords': product.get_keywords_list(),
        'variants': product.variants,
        'comparative_analysis': product.comparative_analysis,
        'image_url': product.image_url,
        'created_at': product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else None
    }
    
    # Ajouter les informations sur le public cible si disponible
    if product.target_audience:
        product_data['target_audience'] = {
            'id': product.target_audience.id,
            'name': product.target_audience.name,
            'age': product.target_audience.age,
            'location': product.target_audience.location,
            'gender': product.target_audience.gender
        }
    
    # Ajouter les informations sur la boutique si disponible
    if product.boutique:
        product_data['boutique'] = {
            'id': product.boutique.id,
            'name': product.boutique.name,
            'description': product.boutique.description
        }
    
    # Créer une réponse JSON avec le bon header pour le téléchargement
    response = jsonify(product_data)
    response.headers['Content-Disposition'] = f'attachment; filename=product_{product.id}.json'
    return response

# Routes pour l'importation AliExpress et l'export Shopify

@app.route('/import_aliexpress_form')
def import_aliexpress_form():
    """Afficher le formulaire d'importation de produits AliExpress"""
    boutiques = Boutique.query.all()
    customers = Customer.query.all()
    
    # Récupérer les 5 derniers imports
    recent_imports = (ImportedProduct.query
                     .order_by(ImportedProduct.imported_at.desc())
                     .limit(5)
                     .all())
    
    return render_template('product_import.html', 
                           boutiques=boutiques, 
                           customers=customers,
                           recent_imports=recent_imports)

@app.route('/import_aliexpress_product', methods=['POST'])
def import_aliexpress_product():
    """Importer et optimiser un produit depuis AliExpress"""
    try:
        aliexpress_url = request.form.get('aliexpress_url')
        product_name = request.form.get('product_name')
        target_market = request.form.get('target_market', 'moyenne_gamme')
        category = request.form.get('category')
        boutique_id = request.form.get('boutique_id')
        target_audience_id = request.form.get('target_audience_id')
        
        # Valider les entrées
        if not aliexpress_url or not product_name:
            flash('L\'URL AliExpress et le nom du produit sont obligatoires.', 'danger')
            return redirect(url_for('import_aliexpress_form'))
        
        # Convertir les IDs en entiers si nécessaire
        if boutique_id and boutique_id.isdigit():
            boutique_id = int(boutique_id)
        else:
            boutique_id = None
            
        if target_audience_id and target_audience_id.isdigit():
            target_audience_id = int(target_audience_id)
        else:
            target_audience_id = None
        
        # Créer le produit dans la base de données
        new_product = Product(
            name=product_name,
            category=category,
            boutique_id=boutique_id,
            target_audience_id=target_audience_id
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        # Créer l'entrée d'importation
        imported_product = ImportedProduct(
            product_id=new_product.id,
            source_url=aliexpress_url,
            source="aliexpress",
            import_status="processing",
            source_id=aliexpress_importer.extract_aliexpress_product_id(aliexpress_url),
            optimization_settings={
                "target_market": target_market,
                "optimize_seo": request.form.get('optimize_seo') == 'on',
                "optimize_price": request.form.get('optimize_price') == 'on',
                "generate_html": request.form.get('generate_html') == 'on',
                "generate_specs": request.form.get('generate_specs') == 'on',
                "generate_faq": request.form.get('generate_faq') == 'on',
                "generate_variants": request.form.get('generate_variants') == 'on'
            }
        )
        
        db.session.add(imported_product)
        db.session.commit()
        
        # Lancer l'importation en arrière-plan
        async def process_import_task():
            try:
                # Mettre à jour le statut
                imported_product.import_status = "processing"
                db.session.commit()
                
                # Extraire les données
                product_data = await aliexpress_importer.extract_aliexpress_product_data(aliexpress_url)
                imported_product.raw_data = product_data
                
                # Optimiser les prix
                pricing_data = await aliexpress_importer.optimize_pricing_strategy(product_data, target_market)
                imported_product.pricing_strategy = pricing_data
                imported_product.original_price = pricing_data.get('original_price', 0)
                imported_product.optimized_price = pricing_data.get('psychological_price', 0)
                imported_product.original_currency = product_data.get('devise', 'EUR')
                
                # Mettre à jour le produit avec les données extraites
                new_product.price = pricing_data.get('psychological_price', 0)
                if product_data.get('images_urls') and len(product_data.get('images_urls', [])) > 0:
                    new_product.image_url = product_data['images_urls'][0]
                new_product.base_description = product_data.get('description', '')
                
                # Générer le contenu HTML optimisé pour Shopify
                if imported_product.optimization_settings.get('generate_html'):
                    template_data = await aliexpress_importer.generate_shopify_html_template(product_data, pricing_data)
                    imported_product.templates = template_data
                    
                    # Mettre à jour les données du produit
                    new_product.meta_title = template_data.get('meta_title', '')
                    new_product.meta_description = template_data.get('meta_description', '')
                    new_product.alt_text = template_data.get('alt_text', '')
                    new_product.keywords = template_data.get('tags', [])
                    new_product.generated_title = template_data.get('meta_title', '')
                    
                    # Ajouter le HTML généré
                    if imported_product.optimization_settings.get('generate_html'):
                        new_product.html_description = template_data.get('html_description', '')
                    
                    if imported_product.optimization_settings.get('generate_specs'):
                        new_product.html_specifications = template_data.get('html_specifications', '')
                    
                    if imported_product.optimization_settings.get('generate_faq'):
                        new_product.html_faq = template_data.get('html_faq', '')
                
                # Finaliser l'importation
                imported_product.import_status = "complete"
                db.session.commit()
                
            except Exception as e:
                # En cas d'erreur, marquer l'importation comme échouée
                imported_product.import_status = "failed"
                imported_product.status_message = str(e)
                db.session.commit()
                logging.error(f"Error importing AliExpress product: {e}")
                raise
        
        # Lancer la tâche asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_import_task())
        loop.close()
        
        flash('Produit importé et optimisé avec succès!', 'success')
        return redirect(url_for('view_product', product_id=new_product.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'importation: {str(e)}', 'danger')
        logging.error(f"Error importing AliExpress product: {e}")
        return redirect(url_for('import_aliexpress_form'))

@app.route('/import_aliexpress_bulk', methods=['POST'])
def import_aliexpress_bulk():
    """Importer plusieurs produits AliExpress par lot"""
    bulk_urls = request.form.get('bulk_urls', '').strip().split('\n')
    bulk_category = request.form.get('bulk_category')
    bulk_boutique_id = request.form.get('bulk_boutique_id')
    
    if not bulk_urls or not bulk_urls[0]:
        flash('Veuillez entrer au moins une URL AliExpress.', 'danger')
        return redirect(url_for('import_aliexpress_form'))
    
    # Convertir l'ID de boutique en entier si nécessaire
    if bulk_boutique_id and bulk_boutique_id.isdigit():
        bulk_boutique_id = int(bulk_boutique_id)
    else:
        bulk_boutique_id = None
    
    imported_count = 0
    failed_count = 0
    
    for url in bulk_urls:
        url = url.strip()
        if not url:
            continue
            
        try:
            # Extraire l'ID du produit pour générer un nom temporaire
            product_id = aliexpress_importer.extract_aliexpress_product_id(url)
            temp_name = f"Produit AliExpress #{product_id}"
            
            # Créer le produit dans la base de données
            new_product = Product(
                name=temp_name,
                category=bulk_category,
                boutique_id=bulk_boutique_id
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            # Créer l'entrée d'importation
            imported_product = ImportedProduct(
                product_id=new_product.id,
                source_url=url,
                source="aliexpress",
                import_status="pending",
                source_id=product_id,
                optimization_settings={
                    "target_market": "moyenne_gamme",
                    "optimize_seo": True,
                    "optimize_price": True,
                    "generate_html": True,
                    "generate_specs": True,
                    "generate_faq": True,
                    "generate_variants": True
                }
            )
            
            db.session.add(imported_product)
            db.session.commit()
            
            imported_count += 1
            
        except Exception as e:
            failed_count += 1
            logging.error(f"Error in bulk import for URL {url}: {e}")
            continue
    
    if imported_count > 0:
        flash(f'{imported_count} produits ont été ajoutés à la file d\'importation. Ils seront traités en arrière-plan.', 'success')
    
    if failed_count > 0:
        flash(f'{failed_count} produits n\'ont pas pu être ajoutés à la file d\'importation.', 'warning')
    
    return redirect(url_for('products'))

@app.route('/shopify_export/<int:product_id>')
def shopify_export(product_id):
    """Afficher la page d'export Shopify pour un produit"""
    product = Product.query.get_or_404(product_id)
    return render_template('product_shopify_export.html', product=product)

@app.route('/update_product_html/<int:product_id>', methods=['POST'])
def update_product_html(product_id):
    """Mettre à jour le HTML d'un produit via AJAX"""
    try:
        data = request.get_json()
        section = data.get('section')
        content = data.get('content')
        
        product = Product.query.get_or_404(product_id)
        
        if section == 'description':
            product.html_description = content
        elif section == 'specifications':
            product.html_specifications = content
        elif section == 'faq':
            product.html_faq = content
        else:
            return jsonify({'success': False, 'error': 'Section non valide'})
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error updating product HTML: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/export_product_json/<int:product_id>')
def export_product_json(product_id):
    """Exporter un produit au format JSON"""
    product = Product.query.get_or_404(product_id)
    
    # Créer un dictionnaire avec toutes les données du produit
    product_data = {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'price': product.price,
        'base_description': product.base_description,
        'meta_title': product.meta_title,
        'meta_description': product.meta_description,
        'alt_text': product.alt_text,
        'keywords': product.get_keywords_list(),
        'html_description': product.html_description,
        'html_specifications': product.html_specifications,
        'html_faq': product.html_faq,
        'image_url': product.image_url,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None
    }
    
    # Générer le nom du fichier
    filename = f"product_{product.id}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Créer une réponse JSON téléchargeable
    response = make_response(json.dumps(product_data, indent=2, ensure_ascii=False))
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'application/json'
    
    return response

@app.route('/regenerate_product_content/<int:product_id>')
def regenerate_product_content(product_id):
    """Régénérer le contenu HTML d'un produit"""
    product = Product.query.get_or_404(product_id)
    
    # Vérifier si le produit a été importé depuis AliExpress
    imported_product = ImportedProduct.query.filter_by(product_id=product.id).first()
    
    if not imported_product or not imported_product.raw_data:
        flash('Impossible de régénérer le contenu: données source non disponibles.', 'danger')
        return redirect(url_for('shopify_export', product_id=product.id))
    
    try:
        # Régénérer le contenu en arrière-plan
        async def regenerate_content():
            try:
                # Récupérer les données
                product_data = imported_product.raw_data
                pricing_data = imported_product.pricing_strategy
                
                # Générer un nouveau template HTML
                template_data = await aliexpress_importer.generate_shopify_html_template(product_data, pricing_data)
                
                # Mettre à jour les templates stockés
                imported_product.templates = template_data
                
                # Mettre à jour les données du produit
                product.meta_title = template_data.get('meta_title', '')
                product.meta_description = template_data.get('meta_description', '')
                product.alt_text = template_data.get('alt_text', '')
                product.keywords = template_data.get('tags', [])
                product.html_description = template_data.get('html_description', '')
                product.html_specifications = template_data.get('html_specifications', '')
                product.html_faq = template_data.get('html_faq', '')
                
                # Sauvegarder les modifications
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error regenerating product content: {e}")
                raise
        
        # Exécuter la tâche asynchrone
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(regenerate_content())
        loop.close()
        
        flash('Contenu régénéré avec succès!', 'success')
        
    except Exception as e:
        flash(f'Erreur lors de la régénération: {str(e)}', 'danger')
        logging.error(f"Error regenerating product content: {e}")
    
    return redirect(url_for('shopify_export', product_id=product.id))

# Routes supprimées pour la gestion des personas (fonctionnalité déplacée dans la page profil client)

@app.route('/metrics_dashboard')
def metrics_dashboard():
    """Page d'analyse des métriques de performance"""
    from models import Metric
    from datetime import datetime, timedelta
    
    # Récupérer les paramètres de filtre
    category = request.args.get('category', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    limit_str = request.args.get('limit', '50')
    
    # Convertir et valider les dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
    except ValueError:
        flash(_("Format de date de début invalide. Utilisation du format par défaut."), "warning")
        start_date = None
    
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if end_date:
            # Ajouter un jour pour inclure toute la journée de fin
            end_date = end_date + timedelta(days=1)
    except ValueError:
        flash(_("Format de date de fin invalide. Utilisation du format par défaut."), "warning")
        end_date = None
    
    # Convertir la limite
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 50
    
    # Construire la requête de base
    query = Metric.query
    
    # Appliquer les filtres
    if category:
        query = query.filter(Metric.category == category)
    if start_date:
        query = query.filter(Metric.created_at >= start_date)
    if end_date:
        query = query.filter(Metric.created_at <= end_date)
    
    # Récupérer le total des métriques (pour les statistiques)
    total_metrics = query.count()
    
    # Valeurs par défaut pour éviter les divisions par zéro
    success_count = 0
    error_count = 0
    success_rate = 0
    avg_time = 0
    category_labels = []
    category_counts = []
    time_labels = []
    time_values = []
    trend_dates = []
    trend_counts = []
    
    # Calculer les statistiques uniquement s'il y a des métriques
    if total_metrics > 0:
        # Récupérer les métriques pour l'affichage (triées par date et limitées)
        metrics = query.order_by(Metric.created_at.desc()).limit(limit).all()
        
        # Calculer les statistiques
        success_count = query.filter(Metric.status == True).count()
        error_count = total_metrics - success_count
        success_rate = (success_count / total_metrics * 100) if total_metrics > 0 else 0
        
        # Calculer le temps moyen
        avg_time_result = db.session.query(db.func.avg(Metric.execution_time)).filter(Metric.execution_time != None).scalar()
        avg_time = avg_time_result if avg_time_result is not None else 0
        
        # Données pour le graphique des catégories
        category_stats = db.session.query(
            Metric.category, db.func.count(Metric.id)
        ).group_by(Metric.category).all()
        
        category_labels = [cat[0] or _("Non catégorisé") for cat in category_stats]
        category_counts = [cat[1] for cat in category_stats]
        
        # Données pour le graphique des temps de réponse
        time_stats = db.session.query(
            Metric.name, db.func.avg(Metric.execution_time)
        ).filter(Metric.execution_time != None).group_by(Metric.name).order_by(db.func.avg(Metric.execution_time).desc()).limit(10).all()
        
        time_labels = [stat[0] for stat in time_stats]
        time_values = [float(stat[1]) for stat in time_stats]
        
        # Données pour le graphique de tendance (nombre de métriques par jour)
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        trend_stats = db.session.query(
            db.func.date_trunc('day', Metric.created_at).label('date'),
            db.func.count(Metric.id)
        ).filter(Metric.created_at >= week_ago).group_by('date').order_by('date').all()
        
        trend_dates = [stat[0].strftime('%Y-%m-%d') for stat in trend_stats]
        trend_counts = [stat[1] for stat in trend_stats]
    else:
        # S'il n'y a pas de métriques, initialiser avec une liste vide
        metrics = []
    
    # Fonction pour déterminer la couleur de la catégorie
    def get_category_color(category):
        if not category:
            return 'secondary'
        
        color_map = {
            'ai': 'primary',
            'generation': 'info',
            'user': 'success',
            'system': 'warning',
            'import': 'danger'
        }
        
        return color_map.get(category.lower(), 'secondary')
    
    return render_template(
        'metrics.html',
        metrics=metrics,
        total_metrics=total_metrics,
        success_count=success_count,
        error_count=error_count,
        success_rate=success_rate,
        avg_time=avg_time,
        category_labels=category_labels,
        category_counts=category_counts,
        time_labels=time_labels,
        time_values=time_values,
        trend_dates=trend_dates,
        trend_counts=trend_counts,
        category=category,
        start_date=start_date_str,
        end_date=end_date_str,
        limit=limit,
        get_category_color=get_category_color
    )

# Routes pour la gestion des personas supprimées (fonctionnalité déplacée dans la page profil client)
# Conservez seulement la fonction get_persona pour l'API JSON
@app.route('/persona/<int:persona_id>')
def get_persona(persona_id):
    """Récupérer les détails d'un persona au format JSON"""
    try:
        from models import CustomerPersona
        
        persona = CustomerPersona.query.get_or_404(persona_id)
        
        # Récupérer les informations de niche et de boutique
        niche_market = None
        if persona.niche_market_id:
            niche = NicheMarket.query.get(persona.niche_market_id)
            if niche:
                niche_market = {
                    'id': niche.id,
                    'name': niche.name
                }
        
        boutique = None
        if persona.boutique_id:
            b = Boutique.query.get(persona.boutique_id)
            if b:
                boutique = {
                    'id': b.id,
                    'name': b.name
                }
        
        # Récupérer les clients associés
        customers = []
        for assoc in persona.customer_associations:
            customer = Customer.query.get(assoc.customer_id)
            if customer:
                customers.append({
                    'id': customer.id,
                    'name': customer.name,
                    'is_primary': assoc.is_primary,
                    'relevance_score': assoc.relevance_score,
                    'notes': assoc.notes
                })
        
        # Créer une réponse JSON avec les données du persona
        result = {
            'id': persona.id,
            'title': persona.title,
            'description': persona.description,
            'primary_goal': persona.primary_goal,
            'pain_points': persona.pain_points,
            'buying_triggers': persona.buying_triggers,
            'age_range': persona.age_range,
            'gender_affinity': persona.gender_affinity,
            'location_type': persona.location_type,
            'income_bracket': persona.income_bracket,
            'education_level': persona.education_level,
            'values': persona.values,
            'interests': persona.interests,
            'lifestyle': persona.lifestyle,
            'personality_traits': persona.personality_traits,
            'buying_habits': persona.buying_habits,
            'brand_affinities': persona.brand_affinities,
            'price_sensitivity': persona.price_sensitivity,
            'decision_factors': persona.decision_factors,
            'preferred_channels': persona.preferred_channels,
            'content_preferences': persona.content_preferences,
            'social_media_behavior': persona.social_media_behavior,
            'niche_specific_attributes': persona.niche_specific_attributes,
            'custom_fields': persona.custom_fields,
            'avatar_url': persona.avatar_url,
            'avatar_prompt': persona.avatar_prompt,
            'created_at': persona.created_at,
            'updated_at': persona.updated_at,
            'niche_market': niche_market,
            'boutique': boutique,
            'customers': customers
        }
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error getting persona details: {e}")
        return jsonify({'error': str(e)}), 500

with app.app_context():
    # Create tables
    db.create_all()
    
    # Add some default niches if none exist
    if NicheMarket.query.count() == 0:
        default_niches = [
            {
                'name': 'Sustainable Fashion',
                'description': 'Eco-friendly and ethically produced clothing and accessories',
                'key_characteristics': 'Eco-conscious, Ethical, Sustainable materials, Fair trade'
            },
            {
                'name': 'Vintage Boutique',
                'description': 'Curated selection of vintage clothing and accessories',
                'key_characteristics': 'Retro, Nostalgic, Unique, Classic'
            },
            {
                'name': 'Luxury Accessories',
                'description': 'High-end designer accessories for the discerning customer',
                'key_characteristics': 'Premium, Exclusive, Craftsmanship, Status'
            },
            {
                'name': 'Athleisure Wear',
                'description': 'Stylish athletic clothing designed for both workout and casual wear',
                'key_characteristics': 'Active, Comfortable, Versatile, Modern'
            }
        ]
        
        for niche_data in default_niches:
            niche = NicheMarket(**niche_data)
            db.session.add(niche)
        
        db.session.commit()

# --------------------------------------------------------------------------------
# Routes pour les outils OSP (Open Strategy Partners)
# --------------------------------------------------------------------------------
from osp_tools import generate_product_value_map, analyze_content_with_osp_guidelines, apply_seo_guidelines, render_value_map_html

@app.route('/osp-tools')
def osp_tools():
    """Page principale des outils OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, NicheMarket, CustomerPersona, OSPAnalysis
    
    # Récupération des données pour les menus déroulants
    boutiques = Boutique.query.all()
    customers = Customer.query.all()
    personas = CustomerPersona.query.all()
    campaigns = Campaign.query.all()
    products = Product.query.all()
    niche_markets = NicheMarket.query.all()
    
    # Analyses OSP récentes
    recent_analyses = OSPAnalysis.query.order_by(OSPAnalysis.created_at.desc()).limit(5).all()
    
    return render_template('osp_tools.html', 
                          boutiques=boutiques,
                          customers=customers,
                          personas=personas,
                          campaigns=campaigns,
                          products=products,
                          niche_markets=niche_markets,
                          recent_analyses=recent_analyses)

@app.route('/osp-tools/value-map-generator')
@app.route('/osp-tools/value-map-generator/<string:source_type>/<int:source_id>')
def value_map_generator(source_type=None, source_id=None):
    """Générateur de carte de valeur produit"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona
    
    # Initialisation des données
    product_name = ""
    product_description = ""
    target_audience = ""
    industry = ""
    niche_market = ""
    key_features = ""
    competitors = ""
    
    # Pré-remplir le formulaire si des données source sont fournies
    if source_type and source_id:
        if source_type == 'product' and source_id:
            product = Product.query.get_or_404(source_id)
            product_name = product.name
            product_description = product.base_description or ""
            if product.target_audience:
                customer = product.target_audience
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
            if product.boutique:
                niche_market = product.boutique.name
        
        elif source_type == 'campaign' and source_id:
            campaign = Campaign.query.get_or_404(source_id)
            product_name = campaign.title
            product_description = campaign.content
            target_audience = campaign.target_audience or ""
            if campaign.customer:
                customer = campaign.customer
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
        
        elif source_type == 'persona' and source_id:
            persona = CustomerPersona.query.get_or_404(source_id)
            product_name = f"Produit pour {persona.title}"
            target_audience = persona.description
            if persona.niche_market:
                niche_market = persona.niche_market.name
    
    # Récupérer les sources de données pour les menus déroulants
    boutiques = Boutique.query.all()
    products = Product.query.all()
    customers = Customer.query.all()
    personas = CustomerPersona.query.all()
    campaigns = Campaign.query.all()
    
    return render_template('osp_tools.html', 
                         form_active='value_map',
                         product_name=product_name,
                         product_description=product_description,
                         target_audience=target_audience,
                         industry=industry,
                         niche_market=niche_market,
                         key_features=key_features,
                         competitors=competitors,
                         boutiques=boutiques,
                         products=products,
                         customers=customers,
                         personas=personas,
                         campaigns=campaigns)

@app.route('/osp-tools/content-analyzer')
@app.route('/osp-tools/content-analyzer/<string:source_type>/<int:source_id>')
def content_analyzer(source_type=None, source_id=None):
    """Analyseur de contenu selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona
    
    # Initialisation des données
    content = ""
    content_type = "product_description"
    target_audience = ""
    industry = ""
    
    # Pré-remplir le formulaire si des données source sont fournies
    if source_type and source_id:
        if source_type == 'product' and source_id:
            product = Product.query.get_or_404(source_id)
            content = product.base_description or product.generated_description or ""
            if product.target_audience:
                customer = product.target_audience
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
            if product.boutique:
                industry = product.boutique.name
        
        elif source_type == 'campaign' and source_id:
            campaign = Campaign.query.get_or_404(source_id)
            content = campaign.content
            content_type = campaign.campaign_type or "email"
            target_audience = campaign.target_audience or ""
            if campaign.customer:
                customer = campaign.customer
                target_audience = f"{customer.name}, {customer.age} ans, {customer.location}"
        
        elif source_type == 'persona' and source_id:
            persona = CustomerPersona.query.get_or_404(source_id)
            content = persona.description
            target_audience = persona.title
            if persona.niche_market:
                industry = persona.niche_market.name
    
    # Récupérer les sources de données pour les menus déroulants
    boutiques = Boutique.query.all()
    products = Product.query.all()
    customers = Customer.query.all()
    personas = CustomerPersona.query.all()
    campaigns = Campaign.query.all()
    
    return render_template('osp_tools.html', 
                         form_active='content_analyzer',
                         content=content,
                         content_type=content_type,
                         target_audience=target_audience,
                         industry=industry,
                         boutiques=boutiques,
                         products=products,
                         customers=customers,
                         personas=personas,
                         campaigns=campaigns)

@app.route('/osp-tools/seo-optimizer')
@app.route('/osp-tools/seo-optimizer/<string:source_type>/<int:source_id>')
def seo_optimizer(source_type=None, source_id=None):
    """Optimiseur SEO selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Campaign, Product
    
    # Initialisation des données
    title = ""
    description = ""
    page_type = "product"
    locale = "fr_FR"
    is_local_business = True
    
    # Pré-remplir le formulaire si des données source sont fournies
    if source_type and source_id:
        if source_type == 'product' and source_id:
            product = Product.query.get_or_404(source_id)
            title = product.name
            description = product.base_description or product.generated_description or ""
            # Si le produit a un méta titre/description, les utiliser
            if product.meta_title:
                title = product.meta_title
            if product.meta_description:
                description = product.meta_description
                
        elif source_type == 'campaign' and source_id:
            campaign = Campaign.query.get_or_404(source_id)
            title = campaign.title
            description = campaign.content[:200] + "..." if len(campaign.content) > 200 else campaign.content
            if campaign.campaign_type == 'landing_page':
                page_type = 'landing'
            elif campaign.campaign_type == 'product_description':
                page_type = 'product'
            
            # Récupérer la langue de la campagne pour le locale
            if campaign.language:
                if campaign.language == 'fr':
                    locale = 'fr_FR'
                elif campaign.language == 'en':
                    locale = 'en_US'
        
        elif source_type == 'boutique' and source_id:
            boutique = Boutique.query.get_or_404(source_id)
            title = boutique.name
            description = boutique.description or ""
            page_type = 'about'
            
            # Récupérer la langue de la boutique pour le locale
            if boutique.language:
                if boutique.language == 'fr':
                    locale = 'fr_FR'
                elif boutique.language == 'en':
                    locale = 'en_US'
    
    # Récupérer les sources de données pour les menus déroulants
    boutiques = Boutique.query.all()
    products = Product.query.all()
    campaigns = Campaign.query.all()
    
    return render_template('osp_tools.html', 
                         form_active='seo_optimizer',
                         title=title,
                         description=description,
                         page_type=page_type,
                         locale=locale,
                         is_local_business=is_local_business,
                         boutiques=boutiques,
                         products=products,
                         campaigns=campaigns)

@app.route('/osp-tools/generate-value-map', methods=['POST'])
def generate_value_map():
    """Générer une carte de valeur produit"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona, OSPAnalysis
    try:
        # Récupérer les données du formulaire
        product_name = request.form.get('product_name')
        product_description = request.form.get('product_description')
        target_audience = request.form.get('target_audience')
        industry = request.form.get('industry')
        niche_market = request.form.get('niche_market')
        
        # Traiter les listes
        key_features = request.form.get('key_features', '').strip().split('\n') if request.form.get('key_features') else None
        competitors = request.form.get('competitors', '').strip().split('\n') if request.form.get('competitors') else None
        
        # S'assurer que les valeurs ne sont pas None
        product_name = product_name or ""
        product_description = product_description or ""
        target_audience = target_audience or ""
        industry = industry or ""
        niche_market = niche_market or ""
        
        # Générer la carte de valeur
        value_map = generate_product_value_map(
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            industry=industry,
            niche_market=niche_market,
            key_features=key_features,
            competitors=competitors
        )
        
        # Générer le HTML pour l'affichage
        value_map_html = render_value_map_html(value_map)
        
        # Log de la métrique
        log_metric(
            metric_name="osp_value_map_generation",
            data={"product_name": product_name, "industry": industry},
            category="marketing",
            status=True,
            response_time=None
        )
        
        return render_template(
            'osp_tools.html',
            value_map=value_map,
            value_map_html=value_map_html,
            value_map_json=json.dumps(value_map, indent=2, ensure_ascii=False)
        )
    except Exception as e:
        flash(_("Erreur lors de la génération de la carte de valeur: {}").format(str(e)), 'danger')
        log_metric(
            metric_name="osp_value_map_generation",
            data={"error": str(e)},
            category="marketing",
            status=False,
            response_time=None
        )
        return redirect(url_for('osp_tools'))

@app.route('/osp-tools/analyze-content', methods=['POST'])
def analyze_content():
    """Analyser du contenu selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Customer, Campaign, Product, CustomerPersona, OSPAnalysis
    try:
        # Récupérer les données du formulaire
        content = request.form.get('content')
        content_type = request.form.get('content_type')
        target_audience = request.form.get('target_audience')
        industry = request.form.get('industry')
        
        # S'assurer que les valeurs ne sont pas None
        content = content or ""
        content_type = content_type or "product_description"
        target_audience = target_audience or ""
        industry = industry or ""
        
        # Analyser le contenu
        content_analysis = analyze_content_with_osp_guidelines(
            content=content,
            content_type=content_type,
            target_audience=target_audience,
            industry=industry
        )
        
        # Log de la métrique
        log_metric(
            metric_name="osp_content_analysis",
            data={"content_type": content_type, "length": len(content)},
            category="marketing",
            status=True,
            response_time=None
        )
        
        return render_template(
            'osp_tools.html',
            content_analysis=content_analysis
        )
    except Exception as e:
        flash(_("Erreur lors de l'analyse du contenu: {}").format(str(e)), 'danger')
        log_metric(
            metric_name="osp_content_analysis",
            data={"error": str(e)},
            category="marketing",
            status=False,
            response_time=None
        )
        return redirect(url_for('osp_tools'))

@app.route('/osp-tools/optimize-seo', methods=['POST'])
def optimize_seo():
    """Optimiser du contenu pour le SEO selon les directives OSP"""
    # Import nécessaire des modèles
    from models import Boutique, Campaign, Product, OSPAnalysis
    try:
        # Récupérer les données du formulaire
        title = request.form.get('title')
        description = request.form.get('description')
        page_type = request.form.get('page_type')
        locale = request.form.get('locale')
        is_local_business = True if request.form.get('is_local_business') else False
        
        # S'assurer que les valeurs ne sont pas None
        title = title or ""
        description = description or ""
        page_type = page_type or "product"
        locale = locale or "fr_FR"
        
        # Optimiser le contenu
        content = {
            "title": title,
            "description": description
        }
        
        seo_optimized = apply_seo_guidelines(
            content=content,
            page_type=page_type,
            locale=locale,
            is_local_business=is_local_business
        )
        
        # Log de la métrique
        log_metric(
            metric_name="osp_seo_optimization",
            data={"page_type": page_type, "locale": locale},
            category="marketing",
            status=True,
            response_time=None
        )
        
        return render_template(
            'osp_tools.html',
            seo_optimized=seo_optimized
        )
    except Exception as e:
        flash(_("Erreur lors de l'optimisation SEO: {}").format(str(e)), 'danger')
        log_metric(
            metric_name="osp_seo_optimization",
            data={"error": str(e)},
            category="marketing",
            status=False,
            response_time=None
        )
        return redirect(url_for('osp_tools'))

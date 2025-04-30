import os
import json
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

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

# Import routes after app initialization
from models import Boutique, NicheMarket, Customer, Campaign, SimilarProduct, Metric, Product, ImportedProduct
import asyncio
import aliexpress_importer
import product_generator
from boutique_ai import (
    generate_customers, 
    generate_customer_persona, 
    generate_marketing_content,
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
def log_metric(metric_name, data):
    """Log a metric to the database for monitoring and analytics"""
    try:
        metric = Metric(
            name=metric_name,
            data=data,
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(metric)
        db.session.commit()
        logging.info(f"Metric logged: {metric_name} - {json.dumps(data)}")
    except Exception as e:
        logging.error(f"Failed to log metric {metric_name}: {e}")
        db.session.rollback()

@app.route('/')
def index():
    return render_template('index.html')

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
        
        # Générer l'avatar avec OpenAI (en arrière-plan ou dans un thread séparé pour ne pas bloquer)
        # Pour l'instant, nous stockons juste l'avatar_prompt, nous implémenterons la génération d'avatar plus tard
        
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
        
        logging.error(f"Error generating enhanced persona for customer {customer_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>')
def view_campaign(campaign_id):
    """Afficher les détails d'une campagne spécifique"""
    campaign = Campaign.query.get_or_404(campaign_id)
    return render_template('campaign_detail.html', campaign=campaign)

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
    from boutique_ai import generate_boutique_image_async, AsyncOpenAI, grok_client
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
            avatar_url = await generate_boutique_image_async(
                client=grok_client,
                image_prompt=enhanced_prompt
            )
            return avatar_url
        
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
        # Log metric pour l'échec de génération
        log_metric("avatar_generation", {
            "success": False,
            "customer_id": customer.id,
            "error": str(e)
        })
        
        logging.error(f"Error generating avatar for customer {customer_id}: {e}")
        return jsonify({'error': str(e)}), 500

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

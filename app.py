import os
import json
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
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
from models import Boutique, NicheMarket, Customer, Campaign, Metric
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
        
        try:
            # Generate customer profiles for the selected niche
            niche = NicheMarket.query.get(niche_id)
            if niche:
                # Generate profiles with AI
                customer_profiles = generate_customers(niche.name, niche.description, num_profiles)
                
                # Log metric for profile generation
                log_metric("profile_generation", {
                    "success": True,
                    "niche_id": niche_id,
                    "niche_name": niche.name,
                    "count": len(customer_profiles),
                    "persist_to_db": persist_to_db
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
            customer.gender = request.form.get('gender', customer.gender)
            customer.language = request.form.get('language', customer.language)
            customer.interests = request.form.get('interests', customer.interests)
            customer.preferred_device = request.form.get('preferred_device', customer.preferred_device)
            customer.persona = request.form.get('persona', customer.persona)
            
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

@app.route('/customer/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    """Supprimer un client"""
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'danger')
    
    return redirect(url_for('profiles'))

@app.route('/campaign/<int:campaign_id>')
def view_campaign(campaign_id):
    """Afficher les détails d'une campagne spécifique"""
    campaign = Campaign.query.get_or_404(campaign_id)
    return render_template('campaign_detail.html', campaign=campaign)

@app.route('/campaign/<int:campaign_id>/delete', methods=['POST'])
def delete_campaign(campaign_id):
    """Supprimer une campagne"""
    campaign = Campaign.query.get_or_404(campaign_id)
    try:
        db.session.delete(campaign)
        db.session.commit()
        flash('Campaign deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting campaign: {str(e)}', 'danger')
    
    return redirect(url_for('campaigns'))

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

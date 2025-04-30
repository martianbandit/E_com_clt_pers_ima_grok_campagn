import os
import logging
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

# Configure the SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///boutique.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Import routes after app initialization
from models import Boutique, NicheMarket, Customer, Campaign
from boutique_ai import (
    generate_customers, 
    generate_customer_persona, 
    generate_marketing_content,
    generate_marketing_image
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    boutiques = Boutique.query.all()
    niches = NicheMarket.query.all()
    return render_template('dashboard.html', boutiques=boutiques, niches=niches)

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    if request.method == 'POST':
        niche_id = int(request.form.get('niche_id', 0))
        num_profiles = int(request.form.get('num_profiles', 5))
        
        try:
            # Generate customer profiles for the selected niche
            niche = NicheMarket.query.get(niche_id)
            if niche:
                customer_profiles = generate_customers(niche.name, niche.description, num_profiles)
                # Store profiles in the session for now
                session['customer_profiles'] = customer_profiles
                flash('Successfully generated customer profiles', 'success')
            else:
                flash('Invalid niche selected', 'danger')
        except Exception as e:
            flash(f'Error generating profiles: {str(e)}', 'danger')
            logging.error(f"Error generating profiles: {e}")
        
        return redirect(url_for('profiles'))
    
    niches = NicheMarket.query.all()
    customer_profiles = session.get('customer_profiles', [])
    return render_template('profiles.html', niches=niches, profiles=customer_profiles)

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
        
        return jsonify({'success': True, 'persona': persona})
    except Exception as e:
        logging.error(f"Error generating persona: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/campaigns', methods=['GET', 'POST'])
def campaigns():
    if request.method == 'POST':
        profile_index = int(request.form.get('profile_index', 0))
        campaign_type = request.form.get('campaign_type', 'email')
        customer_profiles = session.get('customer_profiles', [])
        
        if not customer_profiles or profile_index >= len(customer_profiles):
            flash('Invalid profile selected', 'danger')
            return redirect(url_for('campaigns'))
        
        try:
            profile = customer_profiles[profile_index]
            content = generate_marketing_content(profile, campaign_type)
            
            # Generate an image for the campaign if requested
            image_prompt = request.form.get('image_prompt', '')
            image_url = None
            if image_prompt:
                image_url = generate_marketing_image(profile, image_prompt)
            
            # Create and save the campaign
            campaign = Campaign(
                title=request.form.get('title', f"Campaign for {profile.get('name', 'Customer')}"),
                content=content,
                campaign_type=campaign_type,
                profile_data=profile,
                image_url=image_url
            )
            db.session.add(campaign)
            db.session.commit()
            
            flash('Campaign created successfully', 'success')
        except Exception as e:
            flash(f'Error creating campaign: {str(e)}', 'danger')
            logging.error(f"Error creating campaign: {e}")
        
        return redirect(url_for('campaigns'))
    
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    customer_profiles = session.get('customer_profiles', [])
    return render_template('campaigns.html', campaigns=campaigns, profiles=customer_profiles)

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

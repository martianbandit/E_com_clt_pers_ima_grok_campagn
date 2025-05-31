import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from models_simple import db, User

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# Initialize database
db.init_app(app)

# Configuration de l'internationalisation simple
@app.template_global()
def _(text):
    return text

# Configuration du LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Routes principales
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('simple_index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('simple_dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email and password:
            user = User.query.filter_by(email=email).first()
            
            if user and user.password_hash:
                if check_password_hash(user.password_hash, password):
                    login_user(user, remember=True)
                    flash('Connexion réussie', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Email ou mot de passe incorrect', 'danger')
            else:
                flash('Email ou mot de passe incorrect', 'danger')
        else:
            flash('Veuillez remplir tous les champs', 'warning')
    
    return render_template('simple_login.html')

@app.route('/admin-direct-login')
def admin_direct_login():
    try:
        admin_user = User.query.filter_by(email='admin@markeasy.com').first()
        
        if not admin_user:
            admin_user = User()
            admin_user.id = 'admin'
            admin_user.email = 'admin@markeasy.com'
            admin_user.first_name = 'Admin'
            admin_user.last_name = 'MarkEasy'
            admin_user.password_hash = generate_password_hash('admin123')
            admin_user.created_at = datetime.utcnow()
            admin_user.updated_at = datetime.utcnow()
            
            db.session.merge(admin_user)
            db.session.commit()
        
        login_user(admin_user, remember=True)
        flash('Connexion administrative réussie', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'Erreur lors de la connexion : {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté avec succès', 'info')
    return redirect(url_for('index'))

# Initialisation de la base de données
with app.app_context():
    try:
        db.create_all()
        print("Base de données initialisée avec succès")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la base de données : {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
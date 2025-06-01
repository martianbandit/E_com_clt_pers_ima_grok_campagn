"""
Configuration et fixtures pour les tests NinjaLead
"""
import pytest
import os
import tempfile
from app import app, db

@pytest.fixture
def client():
    """Fixture pour créer un client de test Flask"""
    # Configuration de test
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Base de données temporaire pour les tests
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.config['DATABASE']}"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()
    
    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

@pytest.fixture
def runner():
    """Fixture pour créer un runner CLI de test"""
    return app.test_cli_runner()

@pytest.fixture
def sample_user_data():
    """Données de test pour un utilisateur"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'securepassword123'
    }

@pytest.fixture
def sample_campaign_data():
    """Données de test pour une campagne"""
    return {
        'title': 'Test Campaign',
        'description': 'Campaign de test pour validation',
        'target_audience': 'Test audience',
        'budget': 1000.0
    }
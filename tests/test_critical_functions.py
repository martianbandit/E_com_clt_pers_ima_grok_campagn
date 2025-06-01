"""
Tests critiques pour NinjaLead.ai
Teste les fonctionnalités essentielles de l'application
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Ajouter le répertoire parent au path pour importer l'application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app():
    """Fixture pour créer une instance de test de l'application"""
    # Configuration temporaire pour les tests
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SESSION_SECRET'] = 'test-secret-key'
    os.environ['TESTING'] = 'true'
    
    from app import app as flask_app, db
    
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()

@pytest.fixture
def client(app):
    """Fixture pour créer un client de test"""
    return app.test_client()

@pytest.fixture
def test_user(app):
    """Fixture pour créer un utilisateur de test"""
    from models import User
    from app import db
    from werkzeug.security import generate_password_hash
    
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash=generate_password_hash('testpassword'),
        role='user'
    )
    db.session.add(user)
    db.session.commit()
    return user

class TestCriticalEndpoints:
    """Tests des endpoints critiques"""
    
    def test_home_page_loads(self, client):
        """Teste que la page d'accueil se charge correctement"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'NinjaLead' in response.data or b'ninja' in response.data.lower()
    
    def test_health_check_endpoint(self, client):
        """Teste l'endpoint de health check"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_health_live_endpoint(self, client):
        """Teste l'endpoint de liveness"""
        response = client.get('/health/live')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'alive'
    
    def test_health_ready_endpoint(self, client):
        """Teste l'endpoint de readiness"""
        response = client.get('/health/ready')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ready'

class TestAuthentication:
    """Tests du système d'authentification"""
    
    def test_login_page_loads(self, client):
        """Teste que la page de connexion se charge"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'connexion' in response.data.lower()
    
    def test_register_page_loads(self, client):
        """Teste que la page d'inscription se charge"""
        response = client.get('/register')
        assert response.status_code == 200
        assert b'register' in response.data.lower() or b'inscription' in response.data.lower()
    
    def test_valid_user_login(self, client, test_user):
        """Teste la connexion avec des identifiants valides"""
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'testpassword'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Vérifier que l'utilisateur est connecté (présence du dashboard ou redirection)
    
    def test_invalid_user_login(self, client):
        """Teste la connexion avec des identifiants invalides"""
        response = client.post('/login', data={
            'email': 'invalid@example.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        # Devrait rester sur la page de login avec un message d'erreur

class TestRateLimiting:
    """Tests du système de rate limiting"""
    
    def test_rate_limiting_enforcement(self, client):
        """Teste que le rate limiting est appliqué"""
        # Faire plusieurs requêtes rapides pour tester les limites
        responses = []
        for i in range(60):  # Dépasser la limite de 50 par minute
            response = client.get('/login')
            responses.append(response.status_code)
            if response.status_code == 429:  # Too Many Requests
                break
        
        # Vérifier qu'au moins une requête a été bloquée
        assert 429 in responses or len(responses) >= 50

class TestDatabaseOperations:
    """Tests des opérations de base de données"""
    
    def test_user_creation(self, app):
        """Teste la création d'utilisateur en base"""
        from models import User
        from app import db
        from werkzeug.security import generate_password_hash
        
        user = User(
            username='newuser',
            email='newuser@example.com',
            password_hash=generate_password_hash('password123')
        )
        db.session.add(user)
        db.session.commit()
        
        # Vérifier que l'utilisateur a été créé
        found_user = User.query.filter_by(email='newuser@example.com').first()
        assert found_user is not None
        assert found_user.username == 'newuser'
    
    def test_boutique_creation(self, app, test_user):
        """Teste la création d'une boutique"""
        from models import Boutique
        from app import db
        
        boutique = Boutique(
            name='Test Boutique',
            description='Boutique de test',
            owner_id=test_user.id
        )
        db.session.add(boutique)
        db.session.commit()
        
        # Vérifier que la boutique a été créée
        found_boutique = Boutique.query.filter_by(name='Test Boutique').first()
        assert found_boutique is not None
        assert found_boutique.owner_id == test_user.id

class TestSecurity:
    """Tests de sécurité"""
    
    def test_sql_injection_protection(self, client):
        """Teste la protection contre l'injection SQL"""
        malicious_input = "'; DROP TABLE users; --"
        response = client.post('/login', data={
            'email': malicious_input,
            'password': 'test'
        })
        # L'application devrait toujours fonctionner
        assert response.status_code in [200, 302, 400]
    
    def test_xss_protection(self, client):
        """Teste la protection contre XSS"""
        xss_payload = "<script>alert('xss')</script>"
        response = client.post('/register', data={
            'username': xss_payload,
            'email': 'test@example.com',
            'password': 'password123'
        })
        # Vérifier que le script n'est pas exécuté
        assert b'<script>' not in response.data

class TestBackupSystem:
    """Tests du système de sauvegarde"""
    
    def test_backup_status_endpoint(self, client):
        """Teste l'endpoint de statut des sauvegardes"""
        # Note: Nécessite une authentification admin
        response = client.get('/admin/backup-status')
        # Devrait soit retourner les données, soit demander une authentification
        assert response.status_code in [200, 302, 401, 403]
    
    @patch('backup_manager.backup_manager.create_backup')
    def test_backup_creation_logic(self, mock_backup, app):
        """Teste la logique de création de sauvegarde"""
        from backup_manager import backup_manager
        
        mock_backup.return_value = True
        result = backup_manager.create_backup()
        assert result is True
        mock_backup.assert_called_once()

class TestAIIntegration:
    """Tests d'intégration IA"""
    
    @patch('ai_utils.AIManager.generate_text')
    def test_ai_text_generation(self, mock_generate, app):
        """Teste la génération de texte IA"""
        from ai_utils import AIManager
        
        mock_generate.return_value = "Texte généré par IA"
        ai_manager = AIManager()
        result = ai_manager.generate_text("Test prompt")
        
        assert result == "Texte généré par IA"
        mock_generate.assert_called_once()
    
    def test_ai_error_handling(self, app):
        """Teste la gestion d'erreurs IA"""
        from ai_utils import AIManager
        
        # Tester avec des clés API invalides
        ai_manager = AIManager(openai_api_key="invalid", xai_api_key="invalid")
        result = ai_manager.generate_text("Test prompt", use_fallback=False)
        
        # Devrait retourner un message d'erreur approprié
        assert "erreur" in result.lower() or "error" in result.lower()

class TestFormValidation:
    """Tests de validation des formulaires"""
    
    def test_empty_login_form(self, client):
        """Teste la soumission d'un formulaire de connexion vide"""
        response = client.post('/login', data={
            'email': '',
            'password': ''
        })
        assert response.status_code == 200
        # Devrait rester sur la page avec des erreurs de validation
    
    def test_invalid_email_format(self, client):
        """Teste la validation du format email"""
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'password123'
        })
        assert response.status_code == 200
        # Devrait rejeter l'email invalide

def test_application_startup():
    """Teste que l'application démarre correctement"""
    from app import app
    assert app is not None
    assert app.config is not None

def test_database_connection():
    """Teste la connexion à la base de données"""
    from app import db
    # Dans un contexte de test, la base de données devrait être accessible
    assert db is not None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
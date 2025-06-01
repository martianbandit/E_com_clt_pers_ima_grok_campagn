"""
Tests pour les endpoints principaux de l'API NinjaLead
"""
import pytest
import json

def test_home_page(client):
    """Test de la page d'accueil"""
    response = client.get('/')
    assert response.status_code == 200
    # Vérifier que la page contient des éléments clés
    assert b'NinjaLead' in response.data or b'ninja' in response.data.lower()

def test_login_page_get(client):
    """Test d'accès à la page de connexion"""
    response = client.get('/login')
    assert response.status_code == 200

def test_register_page_get(client):
    """Test d'accès à la page d'inscription"""
    response = client.get('/register')
    assert response.status_code == 200

def test_dashboard_requires_auth(client):
    """Test que le dashboard nécessite une authentification"""
    response = client.get('/dashboard')
    # Doit rediriger vers login ou retourner 401/403
    assert response.status_code in [302, 401, 403]

def test_api_routes_exist(client):
    """Test que les routes API principales existent"""
    api_routes = [
        '/health',
        '/health/live', 
        '/health/ready'
    ]
    
    for route in api_routes:
        response = client.get(route)
        assert response.status_code == 200

def test_protected_routes_require_auth(client):
    """Test que les routes protégées nécessitent une authentification"""
    protected_routes = [
        '/campaign/new',
        '/boutique/new',
        '/generate_customer',
        '/generate_product'
    ]
    
    for route in protected_routes:
        response = client.get(route)
        # Doit rediriger vers login ou retourner 401/403
        assert response.status_code in [302, 401, 403]
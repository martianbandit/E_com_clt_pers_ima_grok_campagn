"""
Tests pour les endpoints de health check et monitoring
"""
import pytest
import json
from datetime import datetime

def test_health_endpoint_basic(client):
    """Test de l'endpoint /health basique"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'database' in data
    assert 'system' in data

def test_health_endpoint_database_metrics(client):
    """Test des métriques de base de données"""
    response = client.get('/health')
    data = json.loads(response.data)
    
    # Vérifier que les métriques DB sont présentes
    db_metrics = data['database']
    assert 'status' in db_metrics
    assert 'response_time_ms' in db_metrics
    assert isinstance(db_metrics['response_time_ms'], (int, float))

def test_health_endpoint_system_metrics(client):
    """Test des métriques système"""
    response = client.get('/health')
    data = json.loads(response.data)
    
    # Vérifier que les métriques système sont présentes
    system_metrics = data['system']
    assert 'cpu_percent' in system_metrics
    assert 'memory_percent' in system_metrics
    assert 'disk_percent' in system_metrics
    
    # Vérifier que les valeurs sont dans des plages raisonnables
    assert 0 <= system_metrics['cpu_percent'] <= 100
    assert 0 <= system_metrics['memory_percent'] <= 100
    assert 0 <= system_metrics['disk_percent'] <= 100

def test_liveness_endpoint(client):
    """Test de l'endpoint /health/live"""
    response = client.get('/health/live')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'alive'
    assert 'timestamp' in data

def test_readiness_endpoint(client):
    """Test de l'endpoint /health/ready"""
    response = client.get('/health/ready')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'ready'
    assert 'timestamp' in data

def test_sentry_test_endpoint(client):
    """Test de l'endpoint de test Sentry (doit retourner une erreur)"""
    response = client.get('/test-sentry')
    assert response.status_code == 500
    
    data = json.loads(response.data)
    assert 'error' in data
    assert 'division by zero' in data['error']
    assert 'Test error sent to Sentry monitoring' in data['message']
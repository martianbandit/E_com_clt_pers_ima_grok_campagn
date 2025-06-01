"""
Tests de performance et benchmarks pour NinjaLead.ai
"""

import pytest
import time
from app import app, db
from models import User, Boutique, Campaign


@pytest.fixture
def client():
    """Client de test avec configuration performance"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


@pytest.fixture
def sample_data():
    """Données d'exemple pour les tests de performance"""
    users = []
    for i in range(10):
        user = User(
            username=f'user_{i}',
            email=f'user_{i}@example.com',
            password_hash='hashed_password'
        )
        db.session.add(user)
        users.append(user)
    
    db.session.commit()
    return users


class TestResponseTimes:
    """Tests de temps de réponse"""
    
    @pytest.mark.benchmark
    def test_home_page_response_time(self, client, benchmark):
        """Benchmark de la page d'accueil"""
        def load_home():
            return client.get('/')
        
        result = benchmark(load_home)
        assert result.status_code in [200, 302]
    
    @pytest.mark.benchmark
    def test_login_page_response_time(self, client, benchmark):
        """Benchmark de la page de connexion"""
        def load_login():
            return client.get('/login')
        
        result = benchmark(load_login)
        assert result.status_code == 200
    
    @pytest.mark.benchmark
    def test_health_check_response_time(self, client, benchmark):
        """Benchmark de l'endpoint de santé"""
        def health_check():
            return client.get('/health')
        
        result = benchmark(health_check)
        assert result.status_code == 200


class TestDatabasePerformance:
    """Tests de performance base de données"""
    
    @pytest.mark.benchmark
    def test_user_query_performance(self, client, sample_data, benchmark):
        """Benchmark des requêtes utilisateur"""
        def query_users():
            return User.query.all()
        
        result = benchmark(query_users)
        assert len(result) == 10
    
    @pytest.mark.benchmark
    def test_user_creation_performance(self, client, benchmark):
        """Benchmark de création d'utilisateur"""
        def create_user():
            user = User(
                username='bench_user',
                email='bench@example.com',
                password_hash='hashed_password'
            )
            db.session.add(user)
            db.session.commit()
            return user
        
        result = benchmark(create_user)
        assert result.id is not None


class TestConcurrency:
    """Tests de charge et concurrence"""
    
    def test_concurrent_requests(self, client):
        """Test de requêtes concurrentes simulées"""
        import threading
        import queue
        
        results = queue.Queue()
        num_requests = 10
        
        def make_request():
            response = client.get('/health')
            results.put(response.status_code)
        
        threads = []
        start_time = time.time()
        
        for _ in range(num_requests):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Vérifier que toutes les requêtes ont réussi
        assert results.qsize() == num_requests
        
        # Vérifier le temps total (doit être raisonnable)
        assert total_time < 5.0  # Moins de 5 secondes pour 10 requêtes
        
        # Vérifier que toutes les réponses sont 200
        while not results.empty():
            assert results.get() == 200


class TestMemoryUsage:
    """Tests d'utilisation mémoire"""
    
    def test_memory_leak_prevention(self, client):
        """Test de prévention des fuites mémoire"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Effectuer plusieurs requêtes
        for _ in range(100):
            response = client.get('/health')
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # La mémoire ne devrait pas augmenter de façon excessive
        # (limite arbitraire de 50MB pour 100 requêtes)
        assert memory_increase < 50 * 1024 * 1024


class TestCachePerformance:
    """Tests de performance du cache"""
    
    def test_cache_hit_performance(self, client):
        """Test de performance des hits de cache"""
        # Premier appel (miss de cache)
        start_time = time.time()
        response1 = client.get('/health')
        first_call_time = time.time() - start_time
        
        # Deuxième appel (hit de cache potentiel)
        start_time = time.time()
        response2 = client.get('/health')
        second_call_time = time.time() - start_time
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Le deuxième appel pourrait être plus rapide avec le cache
        # (test informatif, pas strictement requis)
        print(f"Premier appel: {first_call_time:.4f}s")
        print(f"Deuxième appel: {second_call_time:.4f}s")


if __name__ == '__main__':
    pytest.main([__file__, '--benchmark-only'])
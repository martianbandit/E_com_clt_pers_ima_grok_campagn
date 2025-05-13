import pytest
from app import create_app, db
from app.models import Product

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_list_products(client):
    # Ajoute un produit pour le test
    with client.application.app_context():
        p = Product(name="Test", price=10)
        db.session.add(p)
        db.session.commit()
    rv = client.get('/products/')
    assert rv.status_code == 200
    assert b'Test' in rv.data

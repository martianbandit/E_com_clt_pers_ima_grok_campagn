from app.models import Product
from app import db

def create_product(data):
    product = Product(
        name=data['name'],
        price=data.get('price'),
        category=data.get('category'),
        base_description=data.get('base_description')
    )
    db.session.add(product)
    db.session.commit()
    return product

# TODO: Ajouter validation et gestion d'erreur

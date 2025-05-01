def test_import_models():
    from app.models import Product
    assert Product is not None

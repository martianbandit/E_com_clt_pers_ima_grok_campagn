# E_com_clt_pers_ima_grok_campagn

## Structure
- `app/` : Application Flask (blueprints, logique principale)
- `services/` : Logique métier réutilisable
- `models.py` : Modèles SQLAlchemy
- `tests/` : Tests unitaires et d'intégration

## Lancer l'application
```bash
export FLASK_APP=app:create_app
flask run
```

## Lancer les tests
```bash
pytest
```

## À améliorer
- Ajouter la validation des entrées (WTForms, Marshmallow)
- Protéger les formulaires (CSRF)
- Ajouter des blueprints pour chaque domaine (campagnes, personas, etc.)
- Ajouter des index SQL et des contraintes d'unicité
- Couvrir chaque module par des tests

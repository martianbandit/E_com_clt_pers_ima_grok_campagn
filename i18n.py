from flask_babel import Babel
from flask import request, session, g
import logging

# Langues supportées
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'de': 'Deutsch',
    'it': 'Italiano',
    'pt': 'Português',
    'nl': 'Nederlands',
    'zh': '中文',
    'ja': '日本語',
    'ru': 'Русский'
}

babel = Babel()

def get_locale():
    """
    Détermine la langue à utiliser pour l'utilisateur actuel
    Priorité :
    1. Langue définie explicitement dans la session
    2. Préférence de langue du boutique (si disponible)
    3. Langue du navigateur (si supportée)
    4. Anglais par défaut
    """
    # 1. Langue explicite de la session
    lang = session.get('language')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang
    
    # 2. Préférence de langue de la boutique (si l'utilisateur est associé à une boutique)
    try:
        # Cette partie sera implémentée une fois que nous aurons ajouté la colonne langue aux boutiques
        if hasattr(g, 'current_boutique') and g.current_boutique and hasattr(g.current_boutique, 'language'):
            boutique_lang = g.current_boutique.language
            if boutique_lang and boutique_lang in SUPPORTED_LANGUAGES:
                return boutique_lang
    except Exception as e:
        logging.warning(f"Erreur lors de la récupération de la langue boutique: {str(e)}")
    
    # 3. Langue du navigateur (Accept-Language header)
    if request.accept_languages:
        return request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys())
    
    # 4. Par défaut: anglais
    return 'en'

def get_supported_languages():
    """Renvoie un dictionnaire des langues supportées avec leurs noms natifs"""
    return SUPPORTED_LANGUAGES
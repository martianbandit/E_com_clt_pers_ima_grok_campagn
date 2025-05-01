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
    2. Langue préférée du client actuel (si disponible)
    3. Préférence de langue de la boutique (si disponible)
    4. Langue du navigateur (si supportée)
    5. Anglais par défaut
    """
    # 1. Langue explicite de la session
    lang = session.get('language')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang
    
    # 2. Langue préférée du client actuel
    try:
        if hasattr(g, 'current_customer') and g.current_customer:
            if hasattr(g.current_customer, 'preferred_language') and g.current_customer.preferred_language:
                client_lang = g.current_customer.preferred_language
                if client_lang in SUPPORTED_LANGUAGES:
                    return client_lang
    except Exception as e:
        logging.warning(f"Erreur lors de la récupération de la langue client: {str(e)}")
    
    # 3. Préférence de langue de la boutique
    try:
        if hasattr(g, 'current_boutique') and g.current_boutique:
            # Maintenant que nous avons ajouté la colonne language aux boutiques
            if hasattr(g.current_boutique, 'language') and g.current_boutique.language:
                boutique_lang = g.current_boutique.language
                if boutique_lang in SUPPORTED_LANGUAGES:
                    return boutique_lang
    except Exception as e:
        logging.warning(f"Erreur lors de la récupération de la langue boutique: {str(e)}")
    
    # 4. Langue du navigateur (Accept-Language header)
    if request.accept_languages:
        return request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys())
    
    # 5. Par défaut: anglais
    return 'en'

def get_supported_languages():
    """Renvoie un dictionnaire des langues supportées avec leurs noms natifs"""
    return SUPPORTED_LANGUAGES

def get_language_name(language_code):
    """Renvoie le nom natif d'une langue à partir de son code"""
    if language_code in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[language_code]
    return language_code

def get_boutique_languages(boutique):
    """Renvoie la liste des langues supportées par une boutique"""
    if not boutique or not hasattr(boutique, 'get_supported_languages'):
        return ['en', 'fr']  # Fallback to default languages
    
    return boutique.get_supported_languages()

def is_multilingual_campaign(campaign):
    """Vérifie si une campagne est multilingue"""
    if not campaign:
        return False
    
    return getattr(campaign, 'multilingual_campaign', False)

def get_campaign_target_languages(campaign):
    """Renvoie la liste des langues cibles d'une campagne"""
    if not campaign:
        return ['en']
    
    if not hasattr(campaign, 'target_languages'):
        return [getattr(campaign, 'language', 'en')]
    
    if isinstance(campaign.target_languages, list):
        return campaign.target_languages
    
    try:
        import json
        if isinstance(campaign.target_languages, str):
            return json.loads(campaign.target_languages)
    except:
        pass
    
    return [getattr(campaign, 'language', 'en')]
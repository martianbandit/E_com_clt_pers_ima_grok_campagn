from flask_babel import Babel

babel = Babel()

def get_locale():
    from flask import request, session
    # Attempt to get the language from the session
    lang = session.get('language')
    if lang:
        return lang
    
    # Default to English if no language is specified
    return 'en'
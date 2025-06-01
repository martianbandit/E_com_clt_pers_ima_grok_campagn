"""
Configuration Sentry pour le monitoring et le tracing
Basé sur la documentation officielle de Sentry
"""

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def configure_sentry():
    """Configure Sentry SDK with Flask integration"""
    sentry_sdk.init(
        dsn="https://350994d4ed87e5e65b314481f8251c96@o4509423969107968.ingest.us.sentry.io/4509423982411776",
        # Set traces_sample_rate to 1.0 to capture 100% 
        # of transactions for performance monitoring
        traces_sample_rate=1.0,
        integrations=[
            FlaskIntegration(transaction_style='url'),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,
        attach_stacktrace=True,
        environment="production",
        release="1.0.0"
    )
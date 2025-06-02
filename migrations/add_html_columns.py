"""
Script de migration pour ajouter les colonnes HTML à la table Product
"""

import os
import sys
import logging
from sqlalchemy import Column, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.declarative import declarative_base
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a base class for models
class Base(DeclarativeBase):
    pass

# Create a Flask app and SQLAlchemy instance
app = Flask(__name__)

# Configure the database connection
database_url = os.environ.get("DATABASE_URL")
if database_url is None:
    logging.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

# Check if DATABASE_URL starts with postgres://, and if so, replace with postgresql://
# This is required for SQLAlchemy 1.4.x+
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(model_class=Base)

# Initialize the app with the extension
db.init_app(app)

def run_migration():
    """Execute the database migration to add HTML columns"""
    try:
        with app.app_context():
            # Use raw SQL for the migration to be more flexible and avoid model conflicts
            from sqlalchemy import text
            sql_statements = [
                text("""
                ALTER TABLE product 
                ADD COLUMN IF NOT EXISTS html_description TEXT,
                ADD COLUMN IF NOT EXISTS html_specifications TEXT,
                ADD COLUMN IF NOT EXISTS html_faq TEXT;
                """)
            ]
            
            # Execute each SQL statement
            conn = db.engine.connect()
            for sql in sql_statements:
                conn.execute(sql)
                conn.commit()
            
            logging.info("Migration successful: HTML columns added to Product table")
            return True
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    if run_migration():
        print("Migration completed successfully")
    else:
        print("Migration failed")
        sys.exit(1)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    password_hash = db.Column(db.String, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'
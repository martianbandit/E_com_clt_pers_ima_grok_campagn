from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    """Formulaire de connexion utilisateur"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class RegistrationForm(FlaskForm):
    """Formulaire d'inscription utilisateur"""
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        'Répéter le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('S\'inscrire')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Ce nom d\'utilisateur est déjà utilisé. Veuillez en choisir un autre.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Cette adresse email est déjà utilisée. Veuillez en choisir une autre.')

class EditProfileForm(FlaskForm):
    """Formulaire d'édition du profil utilisateur"""
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    job_title = StringField('Titre du poste', validators=[Length(max=100)])
    company = StringField('Entreprise', validators=[Length(max=100)])
    phone = StringField('Téléphone', validators=[Length(max=20)])
    bio = TextAreaField('Biographie')
    address = TextAreaField('Adresse')
    language_preference = SelectField('Langue préférée', choices=[
        ('fr', 'Français'), 
        ('en', 'English'),
        ('es', 'Español')
    ])
    theme_preference = SelectField('Thème préféré', choices=[
        ('dark', 'Sombre'),
        ('light', 'Clair')
    ])
    submit = SubmitField('Enregistrer les modifications')

class ChangePasswordForm(FlaskForm):
    """Formulaire de changement de mot de passe"""
    current_password = PasswordField('Mot de passe actuel', validators=[DataRequired()])
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(), 
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères')
    ])
    confirm_password = PasswordField('Confirmer le nouveau mot de passe', validators=[
        DataRequired(),
        EqualTo('new_password', message='Les mots de passe doivent correspondre')
    ])
    submit = SubmitField('Changer le mot de passe')
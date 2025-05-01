from typing import Dict, Any
from pydantic import ValidationError
from app.models import CustomerPersona
from app import db
from services.persona_schema import PersonaSchema

def validate_persona_data(data: Dict[str, Any]) -> PersonaSchema:
    """
    Valide et nettoie les données d'un persona (ex: issues de l'IA).
    Lève ValidationError si incohérent.
    """
    return PersonaSchema(**data)


def create_persona(data: Dict[str, Any]) -> CustomerPersona:
    """
    Crée un persona après validation stricte.
    """
    validated = validate_persona_data(data)
    persona = CustomerPersona(**validated.dict())
    db.session.add(persona)
    db.session.commit()
    return persona

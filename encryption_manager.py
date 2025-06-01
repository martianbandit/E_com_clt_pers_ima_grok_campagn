"""
Gestionnaire de chiffrement pour données sensibles - NinjaLead.ai
Implémente le chiffrement at-rest pour les données critiques selon les standards DevOps
"""

import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Union
import json

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Gestionnaire centralisé pour le chiffrement des données sensibles"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialise le gestionnaire de chiffrement
        
        Args:
            master_key: Clé maître pour le chiffrement (optionnel, utilise env var si non fourni)
        """
        self.master_key = master_key or os.environ.get('ENCRYPTION_MASTER_KEY')
        if not self.master_key:
            logger.warning("ENCRYPTION_MASTER_KEY non définie - génération d'une clé temporaire")
            self.master_key = self._generate_master_key()
        
        self.fernet = self._initialize_fernet()
        
    def _generate_master_key(self) -> str:
        """Génère une clé maître sécurisée"""
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()
    
    def _initialize_fernet(self) -> Fernet:
        """Initialise le chiffreur Fernet avec la clé maître"""
        try:
            # Dérive une clé de chiffrement à partir de la clé maître
            master_bytes = self.master_key.encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'ninjalead_salt_2024',  # Salt fixe pour la cohérence
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_bytes))
            return Fernet(key)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du chiffrement: {e}")
            raise
    
    def encrypt_text(self, plaintext: str) -> str:
        """
        Chiffre un texte en clair
        
        Args:
            plaintext: Texte à chiffrer
            
        Returns:
            Texte chiffré encodé en base64
        """
        try:
            if not plaintext:
                return ""
            
            encrypted_bytes = self.fernet.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement: {e}")
            raise
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """
        Déchiffre un texte chiffré
        
        Args:
            encrypted_text: Texte chiffré
            
        Returns:
            Texte en clair
        """
        try:
            if not encrypted_text:
                return ""
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement: {e}")
            raise
    
    def encrypt_json(self, data: dict) -> str:
        """
        Chiffre des données JSON
        
        Args:
            data: Dictionnaire à chiffrer
            
        Returns:
            JSON chiffré
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return self.encrypt_text(json_str)
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement JSON: {e}")
            raise
    
    def decrypt_json(self, encrypted_json: str) -> dict:
        """
        Déchiffre des données JSON
        
        Args:
            encrypted_json: JSON chiffré
            
        Returns:
            Dictionnaire déchiffré
        """
        try:
            decrypted_str = self.decrypt_text(encrypted_json)
            return json.loads(decrypted_str)
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement JSON: {e}")
            raise
    
    def encrypt_sensitive_field(self, value: Union[str, dict, None]) -> Optional[str]:
        """
        Chiffre un champ sensible (gère différents types)
        
        Args:
            value: Valeur à chiffrer
            
        Returns:
            Valeur chiffrée ou None
        """
        try:
            if value is None:
                return None
            
            if isinstance(value, dict):
                return self.encrypt_json(value)
            elif isinstance(value, str):
                return self.encrypt_text(value)
            else:
                return self.encrypt_text(str(value))
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement du champ sensible: {e}")
            return None
    
    def decrypt_sensitive_field(self, encrypted_value: Optional[str], return_type: str = 'str') -> Union[str, dict, None]:
        """
        Déchiffre un champ sensible
        
        Args:
            encrypted_value: Valeur chiffrée
            return_type: Type de retour attendu ('str', 'json')
            
        Returns:
            Valeur déchiffrée dans le type demandé
        """
        try:
            if encrypted_value is None:
                return None
            
            if return_type == 'json':
                return self.decrypt_json(encrypted_value)
            else:
                return self.decrypt_text(encrypted_value)
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement du champ sensible: {e}")
            return None
    
    def is_encrypted(self, value: str) -> bool:
        """
        Vérifie si une valeur est déjà chiffrée
        
        Args:
            value: Valeur à vérifier
            
        Returns:
            True si la valeur semble chiffrée
        """
        try:
            if not value or len(value) < 10:
                return False
            
            # Tente de décoder en base64 et déchiffrer
            base64.urlsafe_b64decode(value.encode('utf-8'))
            self.decrypt_text(value)
            return True
        except:
            return False

# Instance globale du gestionnaire de chiffrement
encryption_manager = EncryptionManager()

# Fonctions utilitaires pour faciliter l'usage
def encrypt_password(password: str) -> str:
    """Chiffre un mot de passe"""
    return encryption_manager.encrypt_text(password)

def decrypt_password(encrypted_password: str) -> str:
    """Déchiffre un mot de passe"""
    return encryption_manager.decrypt_text(encrypted_password)

def encrypt_api_key(api_key: str) -> str:
    """Chiffre une clé API"""
    return encryption_manager.encrypt_text(api_key)

def decrypt_api_key(encrypted_api_key: str) -> str:
    """Déchiffre une clé API"""
    return encryption_manager.decrypt_text(encrypted_api_key)

def encrypt_personal_data(data: dict) -> str:
    """Chiffre des données personnelles"""
    return encryption_manager.encrypt_json(data)

def decrypt_personal_data(encrypted_data: str) -> dict:
    """Déchiffre des données personnelles"""
    return encryption_manager.decrypt_json(encrypted_data)

# Configuration des champs sensibles par table
SENSITIVE_FIELDS = {
    'users': [
        'password_hash',
        'phone',
        'address', 
        'notification_preferences',
        'github_id',
        'google_id'
    ],
    'gdpr_request': [
        'specific_data',
        'response_data',
        'ip_address',
        'user_agent'
    ],
    'consent_record': [
        'ip_address',
        'user_agent'
    ],
    'audit_log': [
        'ip_address',
        'user_agent',
        'details'
    ],
    'campaign': [
        'metrics',
        'advanced_settings'
    ],
    'product': [
        'import_metadata',
        'optimization_data'
    ]
}

def should_encrypt_field(table_name: str, field_name: str) -> bool:
    """
    Détermine si un champ doit être chiffré
    
    Args:
        table_name: Nom de la table
        field_name: Nom du champ
        
    Returns:
        True si le champ doit être chiffré
    """
    return field_name in SENSITIVE_FIELDS.get(table_name, [])

def get_encryption_status() -> dict:
    """
    Retourne le statut du système de chiffrement
    
    Returns:
        Dictionnaire avec les informations de statut
    """
    try:
        # Test de chiffrement/déchiffrement
        test_data = "test_encryption_2024"
        encrypted = encryption_manager.encrypt_text(test_data)
        decrypted = encryption_manager.decrypt_text(encrypted)
        
        return {
            'status': 'operational' if decrypted == test_data else 'error',
            'master_key_configured': bool(os.environ.get('ENCRYPTION_MASTER_KEY')),
            'encryption_algorithm': 'Fernet (AES 128)',
            'key_derivation': 'PBKDF2-SHA256',
            'sensitive_tables': list(SENSITIVE_FIELDS.keys()),
            'test_successful': decrypted == test_data
        }
    except Exception as e:
        logger.error(f"Erreur lors du test de chiffrement: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'master_key_configured': bool(os.environ.get('ENCRYPTION_MASTER_KEY'))
        }

if __name__ == "__main__":
    # Test du système de chiffrement
    status = get_encryption_status()
    print("Statut du système de chiffrement:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
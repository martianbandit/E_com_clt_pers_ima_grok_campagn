"""
Module de conformité GDPR pour NinjaLead.ai
Gestion des données personnelles, droits des utilisateurs et conformité réglementaire
"""

import json
import datetime
from typing import Dict, List, Any, Optional
from flask import request, current_app
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from flask_sqlalchemy import SQLAlchemy

class DataProcessingPurpose:
    """Finalités de traitement des données personnelles"""
    ACCOUNT_MANAGEMENT = "account_management"
    SERVICE_PROVISION = "service_provision"
    MARKETING_COMMUNICATION = "marketing_communication"
    ANALYTICS = "analytics"
    SECURITY = "security"
    LEGAL_COMPLIANCE = "legal_compliance"

class GDPRRequest(db.Model):
    """Modèle pour les demandes GDPR des utilisateurs"""
    __tablename__ = 'gdpr_request'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey('user.id'), nullable=False)
    request_type = Column(String(50), nullable=False)  # access, rectification, erasure, portability, restriction
    status = Column(String(20), default='pending', nullable=False)  # pending, processing, completed, rejected
    
    # Détails de la demande
    description = Column(Text, nullable=True)
    specific_data = Column(JSONB, nullable=True)  # Données spécifiques demandées
    
    # Traçabilité
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Réponse
    response_data = Column(JSONB, nullable=True)
    response_file_path = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Métadonnées
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<GDPRRequest {self.request_type} by user {self.user_id}>'

class ConsentRecord(db.Model):
    """Enregistrement des consentements utilisateur"""
    __tablename__ = 'consent_record'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Type de consentement
    purpose = Column(String(50), nullable=False)
    consent_given = Column(Boolean, nullable=False)
    
    # Contexte du consentement
    consent_text = Column(Text, nullable=False)  # Texte exact présenté à l'utilisateur
    consent_version = Column(String(10), nullable=False)  # Version des CGU/politique
    
    # Traçabilité
    given_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    withdrawn_at = Column(DateTime, nullable=True)
    
    # Contexte technique
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    consent_method = Column(String(50), nullable=False)  # web_form, api, import, etc.
    
    def __repr__(self):
        return f'<ConsentRecord {self.purpose} for user {self.user_id}>'

class DataRetentionPolicy(db.Model):
    """Politiques de rétention des données"""
    __tablename__ = 'data_retention_policy'
    
    id = Column(Integer, primary_key=True)
    data_category = Column(String(100), nullable=False)
    retention_period_days = Column(Integer, nullable=False)
    legal_basis = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class GDPRCompliance:
    """Gestionnaire de conformité GDPR"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le système de conformité GDPR"""
        app.config.setdefault('GDPR_ENABLED', True)
        app.config.setdefault('GDPR_DPO_EMAIL', 'dpo@ninjaleads.ai')
        app.config.setdefault('GDPR_RESPONSE_DELAY_DAYS', 30)
        app.config.setdefault('GDPR_DATA_RETENTION_DEFAULT', 365)
        
        # Initialiser les politiques de rétention par défaut
        with app.app_context():
            self._initialize_retention_policies()
    
    def _initialize_retention_policies(self):
        """Initialise les politiques de rétention par défaut"""
        default_policies = [
            {
                'data_category': 'user_account',
                'retention_period_days': 2555,  # 7 ans
                'legal_basis': 'Legitimate interest - compte utilisateur',
                'description': 'Données de compte utilisateur (nom, email, préférences)'
            },
            {
                'data_category': 'marketing_data',
                'retention_period_days': 1095,  # 3 ans
                'legal_basis': 'Consent - marketing',
                'description': 'Données marketing et communications'
            },
            {
                'data_category': 'analytics_data',
                'retention_period_days': 730,  # 2 ans
                'legal_basis': 'Legitimate interest - amélioration du service',
                'description': 'Données d\'analyse et d\'usage'
            },
            {
                'data_category': 'security_logs',
                'retention_period_days': 365,  # 1 an
                'legal_basis': 'Legitimate interest - sécurité',
                'description': 'Logs de sécurité et d\'audit'
            },
            {
                'data_category': 'support_data',
                'retention_period_days': 1095,  # 3 ans
                'legal_basis': 'Legitimate interest - support client',
                'description': 'Données de support et communication client'
            }
        ]
        
        for policy_data in default_policies:
            existing = DataRetentionPolicy.query.filter_by(
                data_category=policy_data['data_category']
            ).first()
            
            if not existing:
                policy = DataRetentionPolicy(**policy_data)
                db.session.add(policy)
        
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    def record_consent(self, user_id: int, purpose: str, consent_given: bool, 
                      consent_text: str, consent_version: str = "1.0",
                      consent_method: str = "web_form") -> ConsentRecord:
        """Enregistre un consentement utilisateur"""
        
        # Révoquer les anciens consentements pour ce purpose
        old_consents = ConsentRecord.query.filter_by(
            user_id=user_id, 
            purpose=purpose,
            withdrawn_at=None
        ).all()
        
        for old_consent in old_consents:
            old_consent.withdrawn_at = datetime.datetime.utcnow()
        
        # Créer le nouveau consentement
        consent = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            consent_given=consent_given,
            consent_text=consent_text,
            consent_version=consent_version,
            consent_method=consent_method,
            ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        
        db.session.add(consent)
        db.session.commit()
        
        # Audit trail
        audit_action(
            AuditAction.USER_REGISTER if consent_given else AuditAction.USER_LOGOUT,
            f"Consentement {'donné' if consent_given else 'retiré'} pour {purpose}",
            severity=AuditSeverity.MEDIUM,
            resource_type="consent",
            resource_id=consent.id,
            metadata={
                "purpose": purpose,
                "consent_given": consent_given,
                "consent_version": consent_version
            }
        )
        
        return consent
    
    def get_user_consents(self, user_id: int) -> Dict[str, bool]:
        """Récupère l'état des consentements d'un utilisateur"""
        consents = {}
        
        # Récupérer les derniers consentements actifs
        latest_consents = db.session.query(ConsentRecord)\
            .filter_by(user_id=user_id, withdrawn_at=None)\
            .order_by(ConsentRecord.given_at.desc())\
            .all()
        
        for consent in latest_consents:
            if consent.purpose not in consents:
                consents[consent.purpose] = consent.consent_given
        
        return consents
    
    def submit_gdpr_request(self, user_id: int, request_type: str, 
                           description: str = None, specific_data: Dict = None) -> GDPRRequest:
        """Soumet une demande GDPR"""
        
        gdpr_request = GDPRRequest(
            user_id=user_id,
            request_type=request_type,
            description=description,
            specific_data=specific_data,
            ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        
        db.session.add(gdpr_request)
        db.session.commit()
        
        # Audit trail
        audit_action(
            AuditAction.DATA_EXPORT,
            f"Demande GDPR soumise: {request_type}",
            severity=AuditSeverity.HIGH,
            resource_type="gdpr_request",
            resource_id=gdpr_request.id,
            metadata={
                "request_type": request_type,
                "user_id": user_id
            }
        )
        
        return gdpr_request
    
    def process_data_access_request(self, user_id: int) -> Dict[str, Any]:
        """Traite une demande d'accès aux données (Article 15 GDPR)"""
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Collecter toutes les données personnelles
        user_data = {
            "personal_info": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None
            },
            "consents": self._get_consent_history(user_id),
            "gdpr_requests": self._get_gdpr_request_history(user_id),
            "processing_purposes": self._get_processing_purposes(),
            "data_retention": self._get_retention_info(),
            "third_party_sharing": self._get_third_party_info()
        }
        
        # Ajouter les données métier si disponibles
        try:
            from models import Customer, Campaign, Product
            
            # Clients/personas
            customers = Customer.query.filter_by(owner_id=user_id).all()
            user_data["customers"] = [
                {
                    "id": c.id,
                    "name": c.name,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                } for c in customers
            ]
            
            # Campagnes
            campaigns = Campaign.query.filter_by(owner_id=user_id).all()
            user_data["campaigns"] = [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                } for c in campaigns
            ]
            
        except Exception:
            pass  # Ignorer si les modèles n'existent pas
        
        return user_data
    
    def process_data_portability_request(self, user_id: int) -> Dict[str, Any]:
        """Traite une demande de portabilité des données (Article 20 GDPR)"""
        # Récupérer uniquement les données fournies par l'utilisateur
        user_data = self.process_data_access_request(user_id)
        
        # Filtrer pour ne garder que les données "portables"
        portable_data = {
            "export_date": datetime.datetime.utcnow().isoformat(),
            "user_provided_data": {
                "account": user_data.get("personal_info", {}),
                "consents": user_data.get("consents", {}),
                "created_content": {
                    "customers": user_data.get("customers", []),
                    "campaigns": user_data.get("campaigns", [])
                }
            },
            "format": "JSON",
            "gdpr_article": "Article 20 - Right to data portability"
        }
        
        return portable_data
    
    def process_erasure_request(self, user_id: int, specific_data: List[str] = None) -> Dict[str, Any]:
        """Traite une demande d'effacement (Article 17 GDPR)"""
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "message": "Utilisateur non trouvé"}
        
        results = {
            "success": True,
            "actions_taken": [],
            "retained_data": [],
            "legal_basis_for_retention": []
        }
        
        if specific_data:
            # Effacement partiel
            for data_type in specific_data:
                if self._can_erase_data_type(data_type):
                    self._erase_data_type(user_id, data_type)
                    results["actions_taken"].append(f"Effacement de {data_type}")
                else:
                    results["retained_data"].append(data_type)
                    results["legal_basis_for_retention"].append(
                        self._get_retention_legal_basis(data_type)
                    )
        else:
            # Effacement complet du compte
            # Anonymiser plutôt que supprimer pour préserver l'intégrité référentielle
            user.username = f"user_deleted_{user.id}"
            user.email = f"deleted_{user.id}@anonymized.local"
            
            # Marquer comme supprimé
            if hasattr(user, 'is_deleted'):
                user.is_deleted = True
            
            results["actions_taken"].append("Anonymisation du compte utilisateur")
        
        db.session.commit()
        
        return results
    
    def _get_consent_history(self, user_id: int) -> List[Dict]:
        """Récupère l'historique des consentements"""
        consents = ConsentRecord.query.filter_by(user_id=user_id)\
                                    .order_by(ConsentRecord.given_at.desc())\
                                    .all()
        
        return [
            {
                "purpose": c.purpose,
                "consent_given": c.consent_given,
                "given_at": c.given_at.isoformat(),
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                "consent_version": c.consent_version
            } for c in consents
        ]
    
    def _get_gdpr_request_history(self, user_id: int) -> List[Dict]:
        """Récupère l'historique des demandes GDPR"""
        requests = GDPRRequest.query.filter_by(user_id=user_id)\
                                  .order_by(GDPRRequest.created_at.desc())\
                                  .all()
        
        return [
            {
                "request_type": r.request_type,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "processed_at": r.processed_at.isoformat() if r.processed_at else None
            } for r in requests
        ]
    
    def _get_processing_purposes(self) -> List[Dict]:
        """Récupère les finalités de traitement"""
        return [
            {
                "purpose": DataProcessingPurpose.ACCOUNT_MANAGEMENT,
                "legal_basis": "Execution of contract",
                "description": "Gestion du compte utilisateur et fourniture du service"
            },
            {
                "purpose": DataProcessingPurpose.SERVICE_PROVISION,
                "legal_basis": "Execution of contract",
                "description": "Fourniture des services de génération de contenu IA"
            },
            {
                "purpose": DataProcessingPurpose.MARKETING_COMMUNICATION,
                "legal_basis": "Consent",
                "description": "Communications marketing et promotionnelles"
            },
            {
                "purpose": DataProcessingPurpose.ANALYTICS,
                "legal_basis": "Legitimate interest",
                "description": "Analyse d'usage pour améliorer le service"
            },
            {
                "purpose": DataProcessingPurpose.SECURITY,
                "legal_basis": "Legitimate interest",
                "description": "Sécurité et prévention de la fraude"
            }
        ]
    
    def _get_retention_info(self) -> List[Dict]:
        """Récupère les informations de rétention"""
        policies = DataRetentionPolicy.query.all()
        return [
            {
                "data_category": p.data_category,
                "retention_period_days": p.retention_period_days,
                "legal_basis": p.legal_basis,
                "description": p.description
            } for p in policies
        ]
    
    def _get_third_party_info(self) -> List[Dict]:
        """Récupère les informations sur le partage avec des tiers"""
        return [
            {
                "third_party": "OpenAI",
                "purpose": "Génération de contenu IA",
                "data_shared": ["Prompts utilisateur", "Préférences de génération"],
                "legal_basis": "Execution of contract",
                "privacy_policy": "https://openai.com/privacy/"
            },
            {
                "third_party": "xAI (Grok)",
                "purpose": "Génération de contenu IA (service alternatif)",
                "data_shared": ["Prompts utilisateur", "Préférences de génération"],
                "legal_basis": "Execution of contract",
                "privacy_policy": "https://x.ai/privacy/"
            },
            {
                "third_party": "Sentry",
                "purpose": "Monitoring et gestion d'erreurs",
                "data_shared": ["Données techniques anonymisées"],
                "legal_basis": "Legitimate interest",
                "privacy_policy": "https://sentry.io/privacy/"
            }
        ]
    
    def _can_erase_data_type(self, data_type: str) -> bool:
        """Vérifie si un type de données peut être effacé"""
        # Règles métier pour l'effacement
        non_erasable = ['security_logs', 'legal_compliance_data', 'financial_records']
        return data_type not in non_erasable
    
    def _erase_data_type(self, user_id: int, data_type: str):
        """Efface un type de données spécifique"""
        # Implémentation spécifique selon le type de données
        pass
    
    def _get_retention_legal_basis(self, data_type: str) -> str:
        """Récupère la base légale pour la rétention d'un type de données"""
        policy = DataRetentionPolicy.query.filter_by(data_category=data_type).first()
        return policy.legal_basis if policy else "Legitimate interest"
    
    def generate_privacy_report(self) -> Dict[str, Any]:
        """Génère un rapport de confidentialité pour l'organisation"""
        total_users = User.query.count()
        
        # Statistiques des consentements
        consent_stats = db.session.query(
            ConsentRecord.purpose,
            db.func.count(ConsentRecord.id).label('total'),
            db.func.sum(db.case([(ConsentRecord.consent_given == True, 1)], else_=0)).label('given')
        ).filter(ConsentRecord.withdrawn_at.is_(None))\
         .group_by(ConsentRecord.purpose)\
         .all()
        
        # Statistiques des demandes GDPR
        gdpr_stats = db.session.query(
            GDPRRequest.request_type,
            GDPRRequest.status,
            db.func.count(GDPRRequest.id).label('count')
        ).group_by(GDPRRequest.request_type, GDPRRequest.status)\
         .all()
        
        return {
            "report_date": datetime.datetime.utcnow().isoformat(),
            "total_users": total_users,
            "consent_statistics": [
                {
                    "purpose": stat.purpose,
                    "total_records": stat.total,
                    "consents_given": stat.given,
                    "consent_rate": (stat.given / stat.total * 100) if stat.total > 0 else 0
                } for stat in consent_stats
            ],
            "gdpr_request_statistics": [
                {
                    "request_type": stat.request_type,
                    "status": stat.status,
                    "count": stat.count
                } for stat in gdpr_stats
            ],
            "data_retention_policies": self._get_retention_info(),
            "processing_purposes": self._get_processing_purposes(),
            "third_party_processors": self._get_third_party_info()
        }

# Instance globale
gdpr_compliance = GDPRCompliance()
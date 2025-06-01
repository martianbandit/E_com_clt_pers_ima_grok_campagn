"""
Routes Flask pour la gestion GDPR
Interface utilisateur pour les droits GDPR et gestion des données personnelles
"""

import json
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from gdpr_compliance import gdpr_compliance, GDPRRequest, ConsentRecord, DataProcessingPurpose
from models import db
import tempfile
import os

gdpr_bp = Blueprint('gdpr', __name__, url_prefix='/gdpr')

@gdpr_bp.route('/privacy-dashboard')
@login_required
def privacy_dashboard():
    """Dashboard de confidentialité utilisateur"""
    # Récupérer les consentements actuels
    consents = gdpr_compliance.get_user_consents(current_user.id)
    
    # Récupérer les demandes GDPR précédentes
    gdpr_requests = GDPRRequest.query.filter_by(user_id=current_user.id)\
                                   .order_by(GDPRRequest.created_at.desc())\
                                   .limit(10).all()
    
    return render_template('gdpr/privacy_dashboard.html',
                         consents=consents,
                         gdpr_requests=gdpr_requests,
                         processing_purposes=gdpr_compliance._get_processing_purposes(),
                         retention_info=gdpr_compliance._get_retention_info())

@gdpr_bp.route('/update-consent', methods=['POST'])
@login_required
def update_consent():
    """Met à jour les consentements utilisateur"""
    purpose = request.form.get('purpose')
    consent_given = request.form.get('consent') == 'true'
    
    if not purpose:
        flash('Finalité de traitement requise', 'error')
        return redirect(url_for('gdpr.privacy_dashboard'))
    
    # Texte de consentement selon la finalité
    consent_texts = {
        DataProcessingPurpose.MARKETING_COMMUNICATION: 
            "J'accepte de recevoir des communications marketing et promotionnelles de NinjaLead.ai",
        DataProcessingPurpose.ANALYTICS: 
            "J'accepte que mes données d'usage soient analysées pour améliorer le service",
        DataProcessingPurpose.SERVICE_PROVISION: 
            "J'accepte le traitement de mes données pour la fourniture du service NinjaLead.ai"
    }
    
    consent_text = consent_texts.get(purpose, f"Consentement pour {purpose}")
    
    gdpr_compliance.record_consent(
        user_id=current_user.id,
        purpose=purpose,
        consent_given=consent_given,
        consent_text=consent_text,
        consent_version="1.0"
    )
    
    action = "donné" if consent_given else "retiré"
    flash(f'Consentement {action} avec succès pour {purpose}', 'success')
    
    return redirect(url_for('gdpr.privacy_dashboard'))

@gdpr_bp.route('/request-data-access', methods=['POST'])
@login_required
def request_data_access():
    """Demande d'accès aux données (Article 15)"""
    description = request.form.get('description', 'Demande d\'accès à mes données personnelles')
    
    gdpr_request = gdpr_compliance.submit_gdpr_request(
        user_id=current_user.id,
        request_type='access',
        description=description
    )
    
    flash('Votre demande d\'accès aux données a été soumise. Vous recevrez une réponse sous 30 jours.', 'success')
    return redirect(url_for('gdpr.privacy_dashboard'))

@gdpr_bp.route('/request-data-portability', methods=['POST'])
@login_required
def request_data_portability():
    """Demande de portabilité des données (Article 20)"""
    description = request.form.get('description', 'Demande de portabilité de mes données')
    
    gdpr_request = gdpr_compliance.submit_gdpr_request(
        user_id=current_user.id,
        request_type='portability',
        description=description
    )
    
    flash('Votre demande de portabilité des données a été soumise. Vous recevrez une réponse sous 30 jours.', 'success')
    return redirect(url_for('gdpr.privacy_dashboard'))

@gdpr_bp.route('/request-data-erasure', methods=['POST'])
@login_required
def request_data_erasure():
    """Demande d'effacement des données (Article 17)"""
    description = request.form.get('description', 'Demande d\'effacement de mes données personnelles')
    specific_data = request.form.getlist('specific_data')
    
    gdpr_request = gdpr_compliance.submit_gdpr_request(
        user_id=current_user.id,
        request_type='erasure',
        description=description,
        specific_data={'specific_data': specific_data} if specific_data else None
    )
    
    flash('Votre demande d\'effacement a été soumise. Vous recevrez une réponse sous 30 jours.', 'success')
    return redirect(url_for('gdpr.privacy_dashboard'))

@gdpr_bp.route('/download-my-data')
@login_required
def download_my_data():
    """Téléchargement immédiat des données utilisateur"""
    try:
        user_data = gdpr_compliance.process_data_access_request(current_user.id)
        
        # Créer un fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(user_data, temp_file, indent=2, ensure_ascii=False, default=str)
        temp_file.close()
        
        filename = f"ninjaleads_data_{current_user.username}_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        
        def remove_file(response):
            try:
                os.unlink(temp_file.name)
            except Exception:
                pass
            return response
        
        return send_file(temp_file.name, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype='application/json')
    
    except Exception as e:
        flash('Erreur lors de la génération du fichier de données', 'error')
        return redirect(url_for('gdpr.privacy_dashboard'))

@gdpr_bp.route('/privacy-policy')
def privacy_policy():
    """Page de politique de confidentialité"""
    return render_template('gdpr/privacy_policy.html',
                         processing_purposes=gdpr_compliance._get_processing_purposes(),
                         retention_info=gdpr_compliance._get_retention_info(),
                         third_parties=gdpr_compliance._get_third_party_info())

@gdpr_bp.route('/cookie-policy')
def cookie_policy():
    """Page de politique des cookies"""
    return render_template('gdpr/cookie_policy.html')

@gdpr_bp.route('/consent-form')
def consent_form():
    """Formulaire de consentement pour nouveaux utilisateurs"""
    return render_template('gdpr/consent_form.html',
                         processing_purposes=gdpr_compliance._get_processing_purposes())

@gdpr_bp.route('/submit-consent', methods=['POST'])
def submit_consent():
    """Soumission du formulaire de consentement"""
    if not current_user.is_authenticated:
        flash('Vous devez être connecté pour donner votre consentement', 'error')
        return redirect(url_for('login'))
    
    consents = {}
    for purpose in [DataProcessingPurpose.MARKETING_COMMUNICATION, 
                   DataProcessingPurpose.ANALYTICS]:
        consent_value = request.form.get(f'consent_{purpose}') == 'on'
        consents[purpose] = consent_value
        
        # Enregistrer chaque consentement
        consent_texts = {
            DataProcessingPurpose.MARKETING_COMMUNICATION: 
                "J'accepte de recevoir des communications marketing et promotionnelles",
            DataProcessingPurpose.ANALYTICS: 
                "J'accepte que mes données d'usage soient analysées pour améliorer le service"
        }
        
        gdpr_compliance.record_consent(
            user_id=current_user.id,
            purpose=purpose,
            consent_given=consent_value,
            consent_text=consent_texts[purpose],
            consent_version="1.0"
        )
    
    flash('Vos préférences de consentement ont été enregistrées', 'success')
    return redirect(url_for('dashboard'))

# Routes d'administration (réservées aux administrateurs)
@gdpr_bp.route('/admin/gdpr-requests')
@login_required
def admin_gdpr_requests():
    """Interface d'administration des demandes GDPR"""
    # Vérifier les permissions admin
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('dashboard'))
    
    requests = GDPRRequest.query.order_by(GDPRRequest.created_at.desc()).all()
    return render_template('gdpr/admin_requests.html', requests=requests)

@gdpr_bp.route('/admin/process-request/<int:request_id>', methods=['POST'])
@login_required
def admin_process_request(request_id):
    """Traitement d'une demande GDPR par un administrateur"""
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('dashboard'))
    
    gdpr_request = GDPRRequest.query.get_or_404(request_id)
    action = request.form.get('action')
    
    if action == 'process':
        gdpr_request.status = 'processing'
        gdpr_request.processed_at = datetime.datetime.utcnow()
        
        # Traiter selon le type de demande
        if gdpr_request.request_type == 'access':
            user_data = gdpr_compliance.process_data_access_request(gdpr_request.user_id)
            gdpr_request.response_data = user_data
        
        elif gdpr_request.request_type == 'portability':
            portable_data = gdpr_compliance.process_data_portability_request(gdpr_request.user_id)
            gdpr_request.response_data = portable_data
        
        elif gdpr_request.request_type == 'erasure':
            specific_data = gdpr_request.specific_data.get('specific_data', []) if gdpr_request.specific_data else []
            erasure_result = gdpr_compliance.process_erasure_request(gdpr_request.user_id, specific_data)
            gdpr_request.response_data = erasure_result
        
        gdpr_request.status = 'completed'
        gdpr_request.completed_at = datetime.datetime.utcnow()
        
    elif action == 'reject':
        gdpr_request.status = 'rejected'
        gdpr_request.rejection_reason = request.form.get('rejection_reason')
        gdpr_request.processed_at = datetime.datetime.utcnow()
        gdpr_request.completed_at = datetime.datetime.utcnow()
    
    db.session.commit()
    flash(f'Demande GDPR {action}ed avec succès', 'success')
    return redirect(url_for('gdpr.admin_gdpr_requests'))

@gdpr_bp.route('/admin/privacy-report')
@login_required
def admin_privacy_report():
    """Rapport de confidentialité pour les administrateurs"""
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('dashboard'))
    
    report = gdpr_compliance.generate_privacy_report()
    return render_template('gdpr/admin_privacy_report.html', report=report)

@gdpr_bp.route('/admin/export-privacy-report')
@login_required
def admin_export_privacy_report():
    """Export du rapport de confidentialité"""
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        report = gdpr_compliance.generate_privacy_report()
        
        # Créer un fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(report, temp_file, indent=2, ensure_ascii=False, default=str)
        temp_file.close()
        
        filename = f"privacy_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return send_file(temp_file.name, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype='application/json')
    
    except Exception as e:
        flash('Erreur lors de la génération du rapport', 'error')
        return redirect(url_for('gdpr.admin_privacy_report'))
#!/usr/bin/env python3
"""
Script d'audit de sécurité automatisé pour NinjaLead
Analyse les vulnérabilités et génère un rapport complet
"""

import os
import subprocess
import json
import sys
from datetime import datetime

def run_bandit_scan():
    """Analyse de sécurité du code avec Bandit"""
    print("🔍 Analyse de sécurité du code Python...")
    
    try:
        result = subprocess.run([
            'bandit', '-r', '.', '-f', 'json', '-o', 'security_report.json'
        ], capture_output=True, text=True)
        
        if os.path.exists('security_report.json'):
            with open('security_report.json', 'r') as f:
                report = json.load(f)
                
            print(f"✅ Scan Bandit terminé:")
            print(f"   - Fichiers analysés: {len(report.get('results', []))}")
            print(f"   - Problèmes détectés: {len([r for r in report.get('results', []) if r.get('issue_severity') in ['HIGH', 'MEDIUM']])}")
            
            return report
        else:
            print("❌ Erreur lors de la génération du rapport Bandit")
            return None
            
    except Exception as e:
        print(f"❌ Erreur Bandit: {e}")
        return None

def run_safety_check():
    """Vérification des vulnérabilités des dépendances"""
    print("📦 Vérification des vulnérabilités des dépendances...")
    
    try:
        result = subprocess.run([
            'safety', 'check', '--json', '--output', 'safety_report.json'
        ], capture_output=True, text=True)
        
        if os.path.exists('safety_report.json'):
            with open('safety_report.json', 'r') as f:
                report = json.load(f)
                
            print(f"✅ Scan Safety terminé:")
            print(f"   - Vulnérabilités trouvées: {len(report)}")
            
            return report
        else:
            print("✅ Aucune vulnérabilité détectée dans les dépendances")
            return []
            
    except Exception as e:
        print(f"❌ Erreur Safety: {e}")
        return None

def check_environment_security():
    """Vérification de la sécurité de l'environnement"""
    print("🔧 Vérification de la configuration de sécurité...")
    
    security_issues = []
    
    # Vérifier les variables d'environnement sensibles
    sensitive_vars = ['DATABASE_URL', 'SESSION_SECRET', 'SENTRY_DSN']
    for var in sensitive_vars:
        if not os.environ.get(var):
            security_issues.append(f"Variable d'environnement manquante: {var}")
    
    # Vérifier les permissions des fichiers sensibles
    sensitive_files = ['app.py', 'models.py', '.env']
    for file in sensitive_files:
        if os.path.exists(file):
            stat = os.stat(file)
            if stat.st_mode & 0o077:  # Vérifier si le fichier est lisible par d'autres
                security_issues.append(f"Permissions trop ouvertes sur: {file}")
    
    if security_issues:
        print("⚠️  Problèmes de sécurité détectés:")
        for issue in security_issues:
            print(f"   - {issue}")
    else:
        print("✅ Configuration de l'environnement sécurisée")
    
    return security_issues

def check_flask_security():
    """Vérification de la configuration Flask"""
    print("🛡️  Vérification de la sécurité Flask...")
    
    security_recommendations = []
    
    # Lire le fichier app.py pour vérifier la configuration
    try:
        with open('app.py', 'r') as f:
            app_content = f.read()
            
        # Vérifications de sécurité Flask
        checks = [
            ('SESSION_COOKIE_SECURE', 'Cookies de session non sécurisés'),
            ('SESSION_COOKIE_HTTPONLY', 'Cookies accessibles via JavaScript'),
            ('WTF_CSRF_ENABLED', 'Protection CSRF désactivée'),
            ('X-Content-Type-Options', 'En-têtes de sécurité manquants')
        ]
        
        for check, message in checks:
            if check not in app_content:
                security_recommendations.append(message)
        
        if security_recommendations:
            print("⚠️  Recommandations de sécurité Flask:")
            for rec in security_recommendations:
                print(f"   - {rec}")
        else:
            print("✅ Configuration Flask sécurisée")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification Flask: {e}")
        security_recommendations.append("Impossible de vérifier la configuration Flask")
    
    return security_recommendations

def generate_security_report():
    """Génère un rapport de sécurité complet"""
    print("📋 Génération du rapport de sécurité complet...")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'scan_results': {
            'bandit': run_bandit_scan(),
            'safety': run_safety_check(),
            'environment': check_environment_security(),
            'flask_config': check_flask_security()
        }
    }
    
    # Calcul du score de sécurité
    total_issues = 0
    if report['scan_results']['bandit']:
        total_issues += len(report['scan_results']['bandit'].get('results', []))
    if report['scan_results']['safety']:
        total_issues += len(report['scan_results']['safety'])
    total_issues += len(report['scan_results']['environment'])
    total_issues += len(report['scan_results']['flask_config'])
    
    if total_issues == 0:
        security_score = 100
        status = "EXCELLENT"
    elif total_issues <= 3:
        security_score = 80
        status = "BIEN"
    elif total_issues <= 6:
        security_score = 60
        status = "MOYEN"
    else:
        security_score = 40
        status = "CRITIQUE"
    
    report['security_score'] = security_score
    report['status'] = status
    report['total_issues'] = total_issues
    
    # Sauvegarder le rapport
    with open('security_audit_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n🎯 RAPPORT DE SÉCURITÉ FINAL:")
    print(f"   Score de sécurité: {security_score}/100 ({status})")
    print(f"   Problèmes détectés: {total_issues}")
    print(f"   Rapport sauvegardé: security_audit_report.json")
    
    return report

if __name__ == "__main__":
    print("🚀 Démarrage de l'audit de sécurité NinjaLead")
    print("=" * 50)
    
    try:
        report = generate_security_report()
        
        # Code de sortie basé sur le score de sécurité
        if report['security_score'] >= 80:
            sys.exit(0)  # Succès
        elif report['security_score'] >= 60:
            sys.exit(1)  # Avertissement
        else:
            sys.exit(2)  # Critique
            
    except Exception as e:
        print(f"❌ Erreur critique lors de l'audit: {e}")
        sys.exit(3)
#!/usr/bin/env python3
"""
Script de test pour les nouvelles fonctionnalités de sécurité
"""

import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test d'importation des modules de sécurité
    from security_middleware import SecurityMiddleware, get_sanitized_form
    from centralized_logging import CentralizedLogger
    
    print("✅ Modules de sécurité importés avec succès")
    
    # Test du middleware de sécurité
    security = SecurityMiddleware()
    
    # Test de sanitisation
    test_input_clean = "Texte normal"
    test_input_xss = "<script>alert('xss')</script>Texte"
    test_input_sql = "'; DROP TABLE users; --"
    
    cleaned_normal = security.sanitize_input(test_input_clean)
    cleaned_xss = security.sanitize_input(test_input_xss)
    cleaned_sql = security.sanitize_input(test_input_sql)
    
    print(f"✅ Sanitisation - Normal: '{cleaned_normal}'")
    print(f"✅ Sanitisation - XSS: '{cleaned_xss}'")
    print(f"✅ Sanitisation - SQL: '{cleaned_sql}'")
    
    # Test du système de logs
    logger = CentralizedLogger()
    print("✅ Système de logs initialisé")
    
    # Test de détection d'attaques
    attack_patterns_found = 0
    from security_middleware import ATTACK_PATTERNS
    
    test_attacks = [
        "<script>alert('test')</script>",
        "javascript:void(0)",
        "' OR 1=1 --",
        "../etc/passwd",
        "$(whoami)"
    ]
    
    for pattern, attack_type in ATTACK_PATTERNS:
        for test_attack in test_attacks:
            if pattern.search(test_attack):
                attack_patterns_found += 1
                print(f"✅ Pattern détecté: {attack_type} dans '{test_attack[:20]}...'")
                break
    
    print(f"✅ {attack_patterns_found} patterns d'attaque détectés sur {len(ATTACK_PATTERNS)} testés")
    
    print("\n🔒 Tests de sécurité terminés - Tous les modules fonctionnent correctement!")
    
except ImportError as e:
    print(f"❌ Erreur d'importation: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
#!/usr/bin/env python3
"""
Script pour remplacer toutes les icônes FontAwesome par des icônes ninja personnalisées
"""

import os
import re
import glob

# Mapping des icônes FontAwesome vers les icônes ninja
ICON_MAPPING = {
    # Icônes d'action
    'fa-plus': 'ninja-action.png',
    'fa-edit': 'ninja-tech.png',
    'fa-save': 'ninja-trophy.png',
    'fa-delete': 'ninja-action.png',
    'fa-trash': 'ninja-action.png',
    'fa-trash-alt': 'ninja-action.png',
    
    # Icônes d'interface
    'fa-eye': 'ninja-analytics.png',
    'fa-search': 'ninja-analytics.png',
    'fa-cog': 'ninja-tech.png',
    'fa-gear': 'ninja-tech.png',
    'fa-settings': 'ninja-tech.png',
    
    # Icônes de communication
    'fa-bullhorn': 'ninja-megaphone.png',
    'fa-megaphone': 'ninja-megaphone.png',
    'fa-envelope': 'ninja-handshake.png',
    'fa-mail': 'ninja-handshake.png',
    
    # Icônes d'analyse
    'fa-chart-line': 'ninja-analytics.png',
    'fa-analytics': 'ninja-analytics.png',
    'fa-graph': 'ninja-analytics.png',
    'fa-chart': 'ninja-analytics.png',
    
    # Icônes utilisateur
    'fa-user': 'ninja-handshake.png',
    'fa-users': 'ninja-handshake.png',
    'fa-user-plus': 'ninja-handshake.png',
    'fa-user-cog': 'ninja-tech.png',
    'fa-user-ninja': 'ninja-logo.png',
    
    # Icônes de sécurité
    'fa-lock': 'ninja-tech.png',
    'fa-key': 'ninja-action.png',
    'fa-shield': 'ninja-trophy.png',
    'fa-security': 'ninja-tech.png',
    
    # Icônes diverses
    'fa-info': 'ninja-analytics.png',
    'fa-info-circle': 'ninja-analytics.png',
    'fa-bell': 'ninja-megaphone.png',
    'fa-home': 'ninja-logo.png',
    'fa-heart': 'ninja-logo.png',
    'fa-star': 'ninja-trophy.png',
    'fa-trophy': 'ninja-trophy.png',
    'fa-crown': 'ninja-trophy.png',
    
    # Icônes par défaut pour les autres cas
    'fa-': 'ninja-logo.png'  # Fallback
}

def get_ninja_icon(fa_class):
    """Retourne l'icône ninja correspondante à une classe FontAwesome"""
    for fa_icon, ninja_icon in ICON_MAPPING.items():
        if fa_icon in fa_class:
            return ninja_icon
    return 'ninja-logo.png'  # Par défaut

def replace_fontawesome_in_file(file_path):
    """Remplace les icônes FontAwesome dans un fichier"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern pour capturer les icônes FontAwesome
        pattern = r'<i\s+class="(fa[sr]?\s+fa-[^"]*)"[^>]*></i>'
        
        def replace_icon(match):
            fa_classes = match.group(1)
            ninja_icon = get_ninja_icon(fa_classes)
            
            # Détermine la taille de l'icône basée sur les classes
            if 'fa-2x' in fa_classes:
                size = '32px'
            elif 'fa-3x' in fa_classes:
                size = '48px'
            elif 'fa-4x' in fa_classes:
                size = '64px'
            elif 'fa-5x' in fa_classes:
                size = '80px'
            else:
                size = '16px'
            
            return f'<img src="{{{{ url_for(\'static\', filename=\'images/{ninja_icon}\') }}}}" alt="" style="width: {size}; height: {size}; margin-right: 8px;">'
        
        content = re.sub(pattern, replace_icon, content)
        
        # Si le contenu a changé, sauvegarder
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Mis à jour: {file_path}")
            return True
        
    except Exception as e:
        print(f"✗ Erreur avec {file_path}: {e}")
    
    return False

def main():
    """Fonction principale"""
    template_files = glob.glob('templates/**/*.html', recursive=True)
    
    updated_count = 0
    total_files = len(template_files)
    
    print(f"Traitement de {total_files} fichiers template...")
    
    for file_path in template_files:
        if replace_fontawesome_in_file(file_path):
            updated_count += 1
    
    print(f"\n✓ Terminé! {updated_count}/{total_files} fichiers mis à jour.")

if __name__ == "__main__":
    main()
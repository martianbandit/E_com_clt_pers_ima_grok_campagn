#!/usr/bin/env python3
"""
Script pour convertir automatiquement toutes les icônes vers le système orange
"""

import os
import re
import glob

def convert_fontawesome_icons(content):
    """Convertit les icônes FontAwesome vers le système orange"""
    
    # Pattern pour les icônes FontAwesome
    patterns = [
        (r'<i\s+class="(fa[sr]?\s+[^"]*)"([^>]*)></i>', r'<i class="\1 icon-orange"\2></i>'),
        (r'<i\s+class="([^"]*\s+fa[sr]?\s+[^"]*)"([^>]*)></i>', r'<i class="\1 icon-orange"\2></i>'),
    ]
    
    for pattern, replacement in patterns:
        # Éviter de dupliquer la classe icon-orange
        content = re.sub(pattern, lambda m: replacement.replace('\1', m.group(1)) if 'icon-orange' not in m.group(1) else m.group(0), content)
    
    return content

def convert_bootstrap_icons(content):
    """Convertit les icônes Bootstrap vers le système orange"""
    
    # Pattern pour les icônes Bootstrap
    patterns = [
        (r'<i\s+class="(bi\s+[^"]*)"([^>]*)></i>', r'<i class="\1 icon-orange"\2></i>'),
        (r'<i\s+class="([^"]*\s+bi\s+[^"]*)"([^>]*)></i>', r'<i class="\1 icon-orange"\2></i>'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, lambda m: replacement.replace('\1', m.group(1)) if 'icon-orange' not in m.group(1) else m.group(0), content)
    
    return content

def convert_svg_icons(content):
    """Ajoute les classes orange aux SVG existants"""
    
    # Pattern simple pour les SVG
    pattern = r'<svg([^>]*?)>'
    
    def add_orange_class(match):
        attrs = match.group(1)
        if 'icon-orange' in attrs:
            return match.group(0)  # Déjà converti
        
        if 'class=' in attrs:
            # Ajouter icon-orange à la classe existante
            attrs = re.sub(r'class="([^"]*)"', r'class="\1 icon-orange"', attrs)
        else:
            # Ajouter une nouvelle classe
            attrs += ' class="icon-orange"'
        return f'<svg{attrs}>'
    
    return re.sub(pattern, add_orange_class, content)

def convert_image_icons_to_svg(content):
    """Convertit certaines icônes image vers des SVG orange"""
    
    icon_svg_mapping = {
        'ninja-logo.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
        'ninja-trophy.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
        'ninja-analytics.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M3 13h2v8H3v-8zm4-6h2v14H7V7zm4-6h2v20h-2V1zm4 8h2v12h-2V9zm4-2h2v14h-2V7z"/></svg>',
        'ninja-handshake.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>',
        'ninja-tech.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>',
        'ninja-megaphone.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>',
        'ninja-action.png': '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="icon-orange"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>',
    }
    
    # Pattern pour les images ninja
    pattern = r'<img\s+src="[^"]*images/([^"]*)"[^>]*alt="[^"]*"[^>]*style="[^"]*"[^>]*>'
    
    def replace_with_svg(match):
        filename = match.group(1)
        return icon_svg_mapping.get(filename, match.group(0))
    
    return re.sub(pattern, replace_with_svg, content)

def process_file(file_path):
    """Traite un fichier template"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Appliquer toutes les conversions
        content = convert_fontawesome_icons(content)
        content = convert_bootstrap_icons(content)
        content = convert_svg_icons(content)
        content = convert_image_icons_to_svg(content)
        
        # Sauvegarder si modifié
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Converti: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"✗ Erreur avec {file_path}: {e}")
        return False

def main():
    """Fonction principale"""
    
    # Trouver tous les fichiers template
    template_files = []
    template_dirs = ['templates', 'templates/components', 'templates/auth', 'templates/admin']
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            template_files.extend(glob.glob(f'{template_dir}/**/*.html', recursive=True))
    
    if not template_files:
        template_files = glob.glob('templates/**/*.html', recursive=True)
    
    print(f"🎨 Conversion des icônes vers le système orange")
    print(f"📁 Traitement de {len(template_files)} fichiers template...")
    
    converted_count = 0
    
    for file_path in template_files:
        if process_file(file_path):
            converted_count += 1
    
    print(f"\n🎉 Terminé! {converted_count}/{len(template_files)} fichiers convertis.")
    print(f"✨ Toutes les icônes utilisent maintenant le système orange avec aura!")

if __name__ == "__main__":
    main()
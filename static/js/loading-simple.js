/**
 * Système d'indicateurs de chargement simplifié pour MarkEasy
 */

document.addEventListener('DOMContentLoaded', function() {
    // Créer l'overlay de chargement s'il n'existe pas déjà
    if (!document.getElementById('loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        
        const container = document.createElement('div');
        container.className = 'loading-container';
        
        const loader = document.createElement('div');
        loader.className = 'ninja-loader';
        
        const text = document.createElement('div');
        text.id = 'loading-text';
        text.className = 'loading-text';
        text.textContent = 'Traitement en cours...';
        
        container.appendChild(loader);
        container.appendChild(text);
        overlay.appendChild(container);
        
        document.body.appendChild(overlay);
    }
    
    // Écouter les soumissions de formulaires
    document.querySelectorAll('form[data-loading="true"]').forEach(form => {
        form.addEventListener('submit', function() {
            showLoading(this.getAttribute('data-loading-message') || 'Traitement en cours...');
        });
    });
    
    // Écouter les clics de boutons
    document.querySelectorAll('button[data-loading="true"]').forEach(button => {
        button.addEventListener('click', function() {
            if (!this.closest('form')) {
                showLoading(this.getAttribute('data-loading-message') || 'Traitement en cours...');
            }
        });
    });
});

// Fonction pour afficher l'animation de chargement
function showLoading(message) {
    const overlay = document.getElementById('loading-overlay');
    const text = document.getElementById('loading-text');
    
    if (overlay && text) {
        text.textContent = message;
        overlay.classList.add('show');
    }
}

// Fonction pour masquer l'animation de chargement
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
}

// Exposer les fonctions au contexte global
window.showLoading = showLoading;
window.hideLoading = hideLoading;
/**
 * Système d'indicateurs de chargement pour MarkEasy
 * Affiche des animations de chargement pendant les opérations longues
 */

// Créer le conteneur pour l'animation de chargement s'il n'existe pas déjà
function createLoadingOverlay() {
    if (!document.getElementById('ninja-loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'ninja-loading-overlay';
        overlay.className = 'loading-overlay';
        
        const container = document.createElement('div');
        container.className = 'loading-container';
        
        const loader = document.createElement('div');
        loader.className = 'ninja-loader';
        
        const text = document.createElement('div');
        text.id = 'loading-text';
        text.className = 'loading-text';
        text.textContent = 'Traitement en cours';
        
        container.appendChild(loader);
        container.appendChild(text);
        overlay.appendChild(container);
        
        document.body.appendChild(overlay);
    }
    
    return {
        overlay: document.getElementById('ninja-loading-overlay'),
        text: document.getElementById('loading-text')
    };
}

// Afficher l'animation de chargement
function showLoading(message = 'Traitement en cours...') {
    const { overlay, text } = createLoadingOverlay();
    text.textContent = message;
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden'; // Empêcher le défilement
}

// Masquer l'animation de chargement
function hideLoading() {
    const overlay = document.getElementById('ninja-loading-overlay');
    if (overlay) {
        overlay.classList.remove('show');
        document.body.style.overflow = ''; // Réactiver le défilement
    }
    
    // Réinitialiser les boutons en chargement
    document.querySelectorAll('.btn-loading').forEach(button => {
        removeLoadingState(button);
    });
}

// Ajouter un état de chargement à un bouton
function addLoadingState(button) {
    // Sauvegarder le contenu original
    if (!button.getAttribute('data-original-content')) {
        button.setAttribute('data-original-content', button.textContent);
    }
    
    // Ajouter un spinner
    button.classList.add('btn-loading');
    const originalContent = button.textContent;
    
    // Create elements safely to prevent XSS
    const spinner = document.createElement('span');
    spinner.className = 'spinner-border spinner-border-sm';
    spinner.setAttribute('role', 'status');
    spinner.setAttribute('aria-hidden', 'true');
    
    const textSpan = document.createElement('span');
    textSpan.className = 'btn-text';
    textSpan.textContent = originalContent; // Safe text insertion
    
    // Clear button and add new elements
    button.innerHTML = '';
    button.appendChild(spinner);
    button.appendChild(textSpan);
    
    button.disabled = true;
}

// Supprimer l'état de chargement d'un bouton
function removeLoadingState(button) {
    button.classList.remove('btn-loading');
    if (button.getAttribute('data-original-content')) {
        button.textContent = button.getAttribute('data-original-content');
    }
    button.disabled = false;
}

// Initialisation lors du chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Créer le conteneur de chargement
    createLoadingOverlay();
    
    // Configurer les écouteurs d'événements pour les formulaires
    document.querySelectorAll('form[data-loading="true"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            const message = this.getAttribute('data-loading-message') || 'Traitement en cours...';
            showLoading(message);
            
            // Désactiver le bouton de soumission et ajouter un spinner
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                addLoadingState(submitButton);
            }
        });
    });
    
    // Configurer les écouteurs d'événements pour les boutons
    document.querySelectorAll('button[data-loading="true"], a.btn[data-loading="true"]').forEach(button => {
        button.addEventListener('click', function(e) {
            // Ignorer si le bouton est dans un formulaire (déjà géré)
            if (this.closest('form[data-loading="true"]')) {
                return;
            }
            
            // Vérifier si le bouton a un attribut href (lien) ou onclick
            if (this.tagName === 'A' || this.hasAttribute('onclick')) {
                const message = this.getAttribute('data-loading-message') || 'Traitement en cours...';
                showLoading(message);
                addLoadingState(this);
            }
        });
    });
    
    // Intercepter les retours de page pour masquer le chargement
    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            hideLoading();
        }
    });
});

// Exposer des fonctions globales
window.showLoading = showLoading;
window.hideLoading = hideLoading;
/**
 * Gestionnaire d'animations de chargement pour NinjaMark
 * 
 * Ce script gère l'affichage des animations de chargement
 * pendant les opérations qui prennent du temps
 */

class LoadingManager {
    constructor() {
        this.init();
    }

    init() {
        // Créer l'overlay de chargement s'il n'existe pas déjà
        if (!document.querySelector('.loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            
            const container = document.createElement('div');
            container.className = 'loading-container';
            
            const loader = document.createElement('div');
            loader.className = 'ninja-loader';
            
            const text = document.createElement('div');
            text.className = 'loading-text';
            text.textContent = 'Traitement en cours';
            
            container.appendChild(loader);
            container.appendChild(text);
            overlay.appendChild(container);
            
            document.body.appendChild(overlay);
        }
        
        this.overlay = document.querySelector('.loading-overlay');
        this.loadingText = document.querySelector('.loading-text');
        
        // Initialiser les écouteurs pour les formulaires et boutons
        this.setupFormListeners();
        this.setupButtonListeners();
    }

    setupFormListeners() {
        // Écouter les soumissions de formulaires concernant les générations AI
        const forms = document.querySelectorAll('form[data-loading="true"]');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const message = form.getAttribute('data-loading-message') || 'Génération en cours';
                this.showLoading(message);
            });
        });
    }
    
    setupButtonListeners() {
        // Écouter les clics sur les boutons concernant les générations AI
        const buttons = document.querySelectorAll('button[data-loading="true"], a.btn[data-loading="true"]');
        
        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                // Ignorer si le bouton est dans un formulaire (déjà géré)
                if (button.closest('form')) return;
                
                // Vérifier si le bouton a un attribut href (lien) ou onclick
                if (button.tagName === 'A' || button.hasAttribute('onclick')) {
                    const message = button.getAttribute('data-loading-message') || 'Traitement en cours';
                    this.showLoading(message);
                    this.addButtonLoadingState(button);
                }
            });
        });
    }
    
    addButtonLoadingState(button) {
        // Sauvegarder le contenu original
        if (!button.getAttribute('data-original-content')) {
            button.setAttribute('data-original-content', button.innerHTML);
        }
        
        // Ajouter un spinner
        button.classList.add('btn-loading');
        const originalContent = button.innerHTML;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            <span class="btn-text">${originalContent}</span>
        `;
        
        button.disabled = true;
    }
    
    removeButtonLoadingState(button) {
        button.classList.remove('btn-loading');
        if (button.getAttribute('data-original-content')) {
            button.innerHTML = button.getAttribute('data-original-content');
        }
        button.disabled = false;
    }

    showLoading(message = 'Traitement en cours') {
        this.loadingText.textContent = message;
        this.overlay.classList.add('show');
        document.body.style.overflow = 'hidden'; // Empêcher le défilement
    }

    hideLoading() {
        this.overlay.classList.remove('show');
        document.body.style.overflow = ''; // Réactiver le défilement
        
        // Réinitialiser tous les boutons en état de chargement
        const loadingButtons = document.querySelectorAll('.btn-loading');
        loadingButtons.forEach(button => {
            this.removeButtonLoadingState(button);
        });
    }
}

// Initialiser le gestionnaire de chargement
document.addEventListener('DOMContentLoaded', () => {
    window.loadingManager = new LoadingManager();
    
    // Intercepter les retours de page pour masquer le chargement
    window.addEventListener('pageshow', (event) => {
        if (event.persisted || (window.performance && 
            window.performance.navigation.type === window.performance.navigation.TYPE_BACK_FORWARD)) {
            if (window.loadingManager) {
                window.loadingManager.hideLoading();
            }
        }
    });
});

// Fonction globale pour afficher le chargement
function showLoading(message) {
    if (window.loadingManager) {
        window.loadingManager.showLoading(message);
    }
}

// Fonction globale pour masquer le chargement
function hideLoading() {
    if (window.loadingManager) {
        window.loadingManager.hideLoading();
    }
}
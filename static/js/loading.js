/**
 * Gestionnaire des animations de chargement pour les processus d'IA
 */

// Configuration globale des animations de chargement
const loadingConfig = {
    messages: {
        persona: [
            "Génération du persona en cours...",
            "Analyse des caractéristiques démographiques...",
            "Création d'un profil psychologique unique...",
            "Identification des motivations d'achat...",
            "Construction de l'histoire personnelle...",
            "Finalisation du persona..."
        ],
        avatar: [
            "Création de votre avatar personnalisé...",
            "Analyse des caractéristiques du persona...",
            "Conception des attributs visuels...",
            "Génération de l'image...",
            "Optimisation de la représentation...",
            "Finalisation de l'avatar..."
        ],
        marketing: [
            "Création de votre contenu marketing...",
            "Analyse des préférences du client...",
            "Optimisation du message pour la niche...",
            "Adaptation du ton et du style...",
            "Intégration des éléments de marque...",
            "Finalisation du contenu..."
        ],
        image: [
            "Génération de votre image marketing...",
            "Analyse des éléments visuels optimaux...",
            "Conception des composants graphiques...",
            "Optimisation pour votre audience cible...",
            "Application des attributs de marque...",
            "Finalisation de l'image..."
        ],
        products: [
            "Recherche de produits similaires...",
            "Analyse des tendances du marché...",
            "Évaluation de la pertinence...",
            "Vérification de la disponibilité...",
            "Optimisation des recommandations...",
            "Finalisation de la sélection..."
        ]
    },
    defaultDuration: 8000, // 8 secondes par défaut
    messageDuration: 1500, // 1,5 seconde par message
};

/**
 * Class LoadingManager - Gère l'affichage des animations de chargement
 */
class LoadingManager {
    constructor() {
        this.overlay = null;
        this.messageElement = null;
        this.currentLoadingType = null;
        this.messageInterval = null;
        this.currentMessageIndex = 0;
        this.init();
    }

    /**
     * Initialise le gestionnaire de chargement
     */
    init() {
        // Création de l'overlay s'il n'existe pas déjà
        if (!document.getElementById('loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            
            const container = document.createElement('div');
            container.className = 'loading-container';
            
            const spinner = document.createElement('div');
            spinner.className = 'loading-spinner';
            
            const message = document.createElement('div');
            message.id = 'loading-message';
            message.className = 'loading-text';
            message.innerHTML = 'Chargement<span class="loading-dots"></span>';
            
            container.appendChild(spinner);
            container.appendChild(message);
            overlay.appendChild(container);
            
            document.body.appendChild(overlay);
            
            this.overlay = overlay;
            this.messageElement = message;
        } else {
            this.overlay = document.getElementById('loading-overlay');
            this.messageElement = document.getElementById('loading-message');
        }
    }

    /**
     * Démarre l'animation de chargement
     * @param {string} type - Type de chargement (persona, avatar, marketing, image, products)
     * @param {object} options - Options supplémentaires
     */
    start(type = 'default', options = {}) {
        this.currentLoadingType = type;
        this.currentMessageIndex = 0;
        
        // Activation de l'overlay
        this.overlay.classList.add('active');
        
        // Initialisation du message
        this.updateLoadingMessage();
        
        // Démarrage de la rotation des messages
        this.messageInterval = setInterval(() => {
            this.currentMessageIndex++;
            this.updateLoadingMessage();
        }, options.messageDuration || loadingConfig.messageDuration);
        
        return this;
    }

    /**
     * Met à jour le message de chargement
     */
    updateLoadingMessage() {
        const messages = loadingConfig.messages[this.currentLoadingType] || ['Chargement en cours...'];
        const index = this.currentMessageIndex % messages.length;
        this.messageElement.innerHTML = messages[index] + '<span class="loading-dots"></span>';
    }

    /**
     * Arrête l'animation de chargement
     */
    stop() {
        // Désactivation de l'overlay
        this.overlay.classList.remove('active');
        
        // Arrêt de la rotation des messages
        if (this.messageInterval) {
            clearInterval(this.messageInterval);
            this.messageInterval = null;
        }
        
        this.currentLoadingType = null;
        this.currentMessageIndex = 0;
        
        return this;
    }

    /**
     * Applique une animation de chargement à un bouton
     * @param {HTMLElement} button - Élément bouton
     * @param {boolean} isLoading - État de chargement
     */
    toggleButtonLoading(button, isLoading) {
        if (!button) return;
        
        if (isLoading) {
            // Sauvegarder le contenu original du bouton
            if (!button.dataset.originalHtml) {
                button.dataset.originalHtml = button.innerHTML;
            }
            
            button.classList.add('btn-loading');
            const btnText = document.createElement('span');
            btnText.className = 'btn-text';
            btnText.innerHTML = button.dataset.originalHtml;
            button.innerHTML = '';
            button.appendChild(btnText);
            button.disabled = true;
        } else {
            button.classList.remove('btn-loading');
            if (button.dataset.originalHtml) {
                button.innerHTML = button.dataset.originalHtml;
            }
            button.disabled = false;
        }
        
        return this;
    }

    /**
     * Applique une animation de chargement à un conteneur
     * @param {HTMLElement} container - Élément conteneur
     * @param {boolean} isLoading - État de chargement
     */
    toggleContentLoading(container, isLoading) {
        if (!container) return;
        
        if (isLoading) {
            container.classList.add('content-loading');
        } else {
            container.classList.remove('content-loading');
        }
        
        return this;
    }
}

// Création d'une instance globale
const loadingManager = new LoadingManager();

// Exporter pour une utilisation globale
window.loadingManager = loadingManager;
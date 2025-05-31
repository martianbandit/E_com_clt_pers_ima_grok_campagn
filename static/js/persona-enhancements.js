/**
 * Améliorations pour les personas générés - contraste et lisibilité
 */

document.addEventListener('DOMContentLoaded', function() {
    // Pour le formulaire de création de persona
    const createPersonaForm = document.getElementById('createPersonaForm');
    if (createPersonaForm) {
        createPersonaForm.addEventListener('submit', function(event) {
            // Afficher l'animation de chargement
            showLoading('Génération du persona en cours...');
        });
    }
    
    // Améliorer le contraste des contenus générés
    enhanceGeneratedContent();
});

// Observer pour détecter les nouveaux contenus générés
const generatedContentObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            enhanceGeneratedContent();
        }
    });
});

// Configuration de l'observer
const observerConfig = { 
    childList: true, 
    subtree: true 
};

// Démarrer l'observation du contenu de la page
document.addEventListener('DOMContentLoaded', function() {
    generatedContentObserver.observe(document.body, observerConfig);
});

// Fonction pour améliorer le contraste du contenu généré
function enhanceGeneratedContent() {
    // Sélectionner tous les éléments contenant du contenu généré par l'IA
    const generatedElements = document.querySelectorAll('.modal-body p, .persona-description, .generated-content');
    
    generatedElements.forEach(function(element) {
        // Appliquer les classes pour améliorer le contraste
        element.classList.add('ai-generated-text');
    });
    
    // Traiter spécifiquement les sections et titres des persona
    const personaSections = document.querySelectorAll('.modal-body h6, .persona-section h3');
    personaSections.forEach(function(section) {
        section.classList.add('ai-section-title');
    });
    
    // Améliorer le contraste des listes
    const generatedLists = document.querySelectorAll('.modal-body ul, .modal-body ol');
    generatedLists.forEach(function(list) {
        list.parentElement.classList.add('ai-generated-text');
    });
}

// Fonction pour améliorer l'affichage du modal des details de persona
function enhancePersonaModal(personaData) {
    if (!personaData) return;
    
    // Wrapper tout le contenu dans des classes améliorées
    const sections = document.querySelectorAll('[id="viewPersonaBody"] .row');
    sections.forEach(function(section) {
        section.classList.add('persona-section');
    });
    
    const descriptions = document.querySelectorAll('[id="viewPersonaBody"] p:not(.mb-1)');
    descriptions.forEach(function(desc) {
        desc.classList.add('persona-content');
    });
    
    const titles = document.querySelectorAll('[id="viewPersonaBody"] h6');
    titles.forEach(function(title) {
        title.classList.add('ai-section-title');
    });
}

// Exposer la fonction pour l'utiliser dans le template
window.enhancePersonaModal = enhancePersonaModal;
// JavaScript pour les interactions "Ninja Marketing"

document.addEventListener('DOMContentLoaded', function() {
    // Ajouter l'effet d'animation au défilement pour le logo MarkEasy
    let lastScrollTop = 0;
    window.addEventListener('scroll', function() {
        const st = window.pageYOffset || document.documentElement.scrollTop;
        const logo = document.querySelector('.markeasy-logo');
        
        // Si on défile plus de 100px et on défile vers le bas
        if (st > 100 && st > lastScrollTop) {
            if (logo) {
                logo.classList.add('scroll-animated');
                setTimeout(function() {
                    logo.classList.remove('scroll-animated');
                }, 1000);
            }
        }
        lastScrollTop = st <= 0 ? 0 : st;
    }, false);
    
    // Fonction pour gérer l'animation des cartes ninja
    function initNinjaCardEffects() {
        const ninjaCards = document.querySelectorAll('.ninja-card, .card');
        ninjaCards.forEach(card => {
            // Ajouter une ombre colorée au survol
            card.addEventListener('mouseenter', function(e) {
                // Créer un effet subtil d'ombre orange
                this.style.boxShadow = '0 10px 25px rgba(255, 107, 0, 0.1)';
            });
            
            // Réinitialiser l'ombre à la sortie
            card.addEventListener('mouseleave', function(e) {
                this.style.boxShadow = '';
            });
        });
    }
    
    // Fonction pour créer un toast ninja personnalisé
    window.showNinjaToast = function(message, type = 'info') {
        // Supprimer tous les toasts existants
        const existingToasts = document.querySelectorAll('.ninja-toast');
        existingToasts.forEach(toast => toast.remove());
        
        // Créer un nouveau toast
        const toast = document.createElement('div');
        toast.className = `ninja-toast ninja-toast-${type}`;
        
        // Déterminer l'icône en fonction du type
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'exclamation-circle';
        if (type === 'warning') icon = 'exclamation-triangle';
        
        // Déterminer les titres traduits
        let typeTitle = type;
        switch(type) {
            case 'success':
                typeTitle = 'Succès';
                break;
            case 'error':
                typeTitle = 'Erreur';
                break;
            case 'warning':
                typeTitle = 'Avertissement';
                break;
            case 'info':
                typeTitle = 'Information';
                break;
            default:
                typeTitle = type.charAt(0).toUpperCase() + type.slice(1);
        }
        
        // Créer les éléments du toast en toute sécurité
        const toastHeader = document.createElement('div');
        toastHeader.className = 'ninja-toast-header';
        
        const titleSpan = document.createElement('span');
        titleSpan.className = 'ninja-toast-title';
        
        const icon_i = document.createElement('i');
        icon_i.className = `fas fa-${icon} me-2`;
        titleSpan.appendChild(icon_i);
        
        titleSpan.appendChild(document.createTextNode(typeTitle));
        toastHeader.appendChild(titleSpan);
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('aria-label', 'Fermer');
        closeButton.onclick = function() { this.parentElement.parentElement.remove(); };
        toastHeader.appendChild(closeButton);
        
        const toastBody = document.createElement('div');
        toastBody.className = 'ninja-toast-body';
        toastBody.textContent = message;
        
        toast.appendChild(toastHeader);
        toast.appendChild(toastBody);
        
        // Ajouter le toast au DOM
        document.body.appendChild(toast);
        
        // Afficher le toast avec une transition
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Auto-fermer après 5 secondes
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    }
    
    // Remplacer la fonction d'alerte standard si elle existe
    if (window.showAlert) {
        const originalShowAlert = window.showAlert;
        window.showAlert = function(message, type) {
            // Mapper les types d'alertes Bootstrap aux types de toast
            const toastType = type === 'danger' ? 'error' : type;
            showNinjaToast(message, toastType);
        };
    }
    
    // Ajouter un petit effet visuel sur les boutons
    function initNinjaButtonEffects() {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.addEventListener('click', function() {
                // Ajouter une petite animation lors du clic
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            });
        });
    }
    
    // Ajouter des interactions pour le logo MarkEasy du footer
    function initLogoEffects() {
        const footerLogo = document.querySelector('.markeasy-logo-large');
        if (footerLogo) {
            footerLogo.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
            });
            
            footerLogo.addEventListener('mouseleave', function() {
                this.style.transform = '';
            });
            
            // Ajouter une interaction de clic pour une animation spéciale
            footerLogo.addEventListener('click', function(e) {
                if (!e.ctrlKey) { // Ne pas interférer avec le clic + ctrl (ouvrir dans un nouvel onglet)
                    e.preventDefault();
                    this.style.transform = 'rotate(360deg)';
                    setTimeout(() => {
                        this.style.transform = '';
                        window.location = '/';
                    }, 500);
                }
            });
        }
    }
    
    // Initialiser tous les effets interactifs
    initNinjaCardEffects();
    initNinjaButtonEffects();
    initLogoEffects();
});
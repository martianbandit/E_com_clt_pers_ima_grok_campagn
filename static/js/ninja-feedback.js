/**
 * Système de feedback ninja personnalisé avec intégration Sentry
 */

class NinjaFeedbackManager {
    constructor() {
        this.modal = null;
        this.form = null;
        this.isInitialized = false;
        this.init();
    }

    init() {
        // Attendre que le DOM soit chargé
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupFeedback());
        } else {
            this.setupFeedback();
        }
    }

    setupFeedback() {
        this.modal = document.getElementById('ninjaFeedbackModal');
        this.form = document.getElementById('ninjaFeedbackForm');
        
        if (!this.modal || !this.form) {
            console.warn('Modal ou formulaire de feedback non trouvé');
            return;
        }

        this.setupEventListeners();
        this.setupFeedbackButtons();
        this.isInitialized = true;
        console.log('✅ Système de feedback ninja initialisé');
    }

    setupEventListeners() {
        // Gestion du changement de type de feedback
        const feedbackTypes = document.querySelectorAll('input[name="feedbackType"]');
        feedbackTypes.forEach(radio => {
            radio.addEventListener('change', (e) => this.updateFormForType(e.target.value));
        });

        // Gestion de la soumission du formulaire
        const submitBtn = document.getElementById('submitFeedbackBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => this.handleSubmit(e));
        }

        // Gestion de l'ouverture du modal
        this.modal.addEventListener('show.bs.modal', () => this.resetForm());
    }

    setupFeedbackButtons() {
        // Bouton dans le header
        const headerBtn = document.getElementById('header-feedback-btn');
        if (headerBtn) {
            headerBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openFeedbackModal('bug');
            });
        }

        // Bouton dans le footer
        const footerBtn = document.getElementById('footer-feedback-btn');
        if (footerBtn) {
            footerBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openFeedbackModal('suggestion');
            });
        }
    }

    openFeedbackModal(type = 'bug') {
        if (!this.isInitialized) {
            console.warn('Système de feedback non initialisé');
            return;
        }

        // Configurer le type de feedback par défaut
        const radioElement = document.getElementById(type === 'bug' ? 'bugReport' : 'suggestion');
        if (radioElement) {
            radioElement.checked = true;
            this.updateFormForType(type);
        }

        // Ouvrir le modal
        const modalInstance = new bootstrap.Modal(this.modal);
        modalInstance.show();
    }

    updateFormForType(type) {
        const titleElement = document.getElementById('feedbackModalTitle');
        const messageLabelElement = document.getElementById('feedbackMessageLabel');
        const submitBtnTextElement = document.getElementById('submitBtnText');
        const messageTextarea = document.getElementById('feedbackMessage');

        switch (type) {
            case 'bug':
                titleElement.textContent = 'Signaler un problème';
                messageLabelElement.textContent = 'Décrivez le problème rencontré';
                submitBtnTextElement.textContent = 'Envoyer le rapport';
                messageTextarea.placeholder = 'Décrivez en détail le problème que vous avez rencontré...';
                break;
            case 'suggestion':
                titleElement.textContent = 'Suggestion d\'amélioration';
                messageLabelElement.textContent = 'Partagez votre suggestion';
                submitBtnTextElement.textContent = 'Envoyer la suggestion';
                messageTextarea.placeholder = 'Décrivez votre idée d\'amélioration...';
                break;
            case 'general':
                titleElement.textContent = 'Commentaire général';
                messageLabelElement.textContent = 'Partagez vos commentaires';
                submitBtnTextElement.textContent = 'Envoyer le commentaire';
                messageTextarea.placeholder = 'Partagez vos commentaires ou questions...';
                break;
        }
    }

    resetForm() {
        this.form.reset();
        
        // Réinitialiser au type "bug" par défaut
        const bugRadio = document.getElementById('bugReport');
        if (bugRadio) {
            bugRadio.checked = true;
            this.updateFormForType('bug');
        }

        // Enlever les états d'erreur
        const inputs = this.form.querySelectorAll('.ninja-input, .ninja-textarea');
        inputs.forEach(input => {
            input.classList.remove('is-invalid');
        });
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        if (!this.validateForm()) {
            return;
        }

        const submitBtn = document.getElementById('submitFeedbackBtn');
        const originalText = submitBtn.textContent;
        
        // État de chargement
        submitBtn.classList.add('loading');
        submitBtn.innerHTML = `
            <svg class="ninja-icon ninja-icon-xs me-2" fill="currentColor">
                <use href="#ninja-loading"></use>
            </svg>
            Envoi en cours...
        `;
        submitBtn.disabled = true;

        try {
            const feedbackData = this.collectFormData();
            await this.sendFeedback(feedbackData);
            
            // Succès
            this.showSuccessMessage();
            setTimeout(() => {
                const modalInstance = bootstrap.Modal.getInstance(this.modal);
                modalInstance.hide();
            }, 2000);
            
        } catch (error) {
            console.error('Erreur lors de l\'envoi du feedback:', error);
            this.showErrorMessage('Une erreur est survenue lors de l\'envoi. Veuillez réessayer.');
        } finally {
            // Restaurer le bouton
            submitBtn.classList.remove('loading');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    validateForm() {
        const name = document.getElementById('feedbackName');
        const email = document.getElementById('feedbackEmail');
        const message = document.getElementById('feedbackMessage');
        
        let isValid = true;

        // Validation du nom
        if (!name.value.trim()) {
            this.showFieldError(name, 'Le nom est requis');
            isValid = false;
        } else {
            this.clearFieldError(name);
        }

        // Validation de l'email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!email.value.trim()) {
            this.showFieldError(email, 'L\'email est requis');
            isValid = false;
        } else if (!emailRegex.test(email.value)) {
            this.showFieldError(email, 'Format d\'email invalide');
            isValid = false;
        } else {
            this.clearFieldError(email);
        }

        // Validation du message
        if (!message.value.trim()) {
            this.showFieldError(message, 'Le message est requis');
            isValid = false;
        } else if (message.value.trim().length < 10) {
            this.showFieldError(message, 'Le message doit contenir au moins 10 caractères');
            isValid = false;
        } else {
            this.clearFieldError(message);
        }

        return isValid;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        // Supprimer le message d'erreur existant
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }

        // Ajouter le nouveau message d'erreur
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    collectFormData() {
        const formData = new FormData(this.form);
        const feedbackType = document.querySelector('input[name="feedbackType"]:checked').value;
        
        // Collecter les informations système
        const systemInfo = {
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            viewport: `${window.innerWidth}x${window.innerHeight}`,
            language: navigator.language,
            platform: navigator.platform
        };

        return {
            type: feedbackType,
            name: document.getElementById('feedbackName').value.trim(),
            email: document.getElementById('feedbackEmail').value.trim(),
            message: document.getElementById('feedbackMessage').value.trim(),
            screenshot: document.getElementById('feedbackScreenshot').files[0] || null,
            systemInfo: systemInfo
        };
    }

    async sendFeedback(feedbackData) {
        // Préparer les données pour Sentry
        const sentryData = {
            message: `[${feedbackData.type.toUpperCase()}] ${feedbackData.message}`,
            level: feedbackData.type === 'bug' ? 'error' : 'info',
            tags: {
                feedback_type: feedbackData.type,
                source: 'ninja_feedback_form'
            },
            user: {
                email: feedbackData.email,
                username: feedbackData.name
            },
            extra: {
                feedback_message: feedbackData.message,
                system_info: feedbackData.systemInfo
            }
        };

        // Envoyer vers Sentry si disponible
        if (typeof Sentry !== 'undefined') {
            try {
                Sentry.captureMessage(sentryData.message, {
                    level: sentryData.level,
                    tags: sentryData.tags,
                    user: sentryData.user,
                    extra: sentryData.extra
                });
                console.log('✅ Feedback envoyé vers Sentry');
            } catch (error) {
                console.warn('Erreur Sentry:', error);
            }
        }

        // Envoyer vers notre endpoint backend
        try {
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(feedbackData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('✅ Feedback envoyé vers le backend:', result);
            return result;
        } catch (error) {
            console.warn('Erreur backend:', error);
            // Ne pas faire échouer si seul le backend échoue
            return { success: true, message: 'Feedback enregistré' };
        }
    }

    showSuccessMessage() {
        const modalBody = this.modal.querySelector('.ninja-feedback-body');
        const successHTML = `
            <div class="text-center py-4">
                <svg class="ninja-icon ninja-icon-lg mb-3" fill="#38a169" style="width: 4rem; height: 4rem;">
                    <use href="#ninja-success"></use>
                </svg>
                <h5 class="text-success">Merci pour votre retour !</h5>
                <p class="text-muted">Notre équipe ninja examine votre message et vous contactera si nécessaire.</p>
            </div>
        `;
        modalBody.innerHTML = successHTML;
    }

    showErrorMessage(message) {
        // Afficher un toast d'erreur
        const toast = document.createElement('div');
        toast.className = 'toast-container position-fixed top-0 end-0 p-3';
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header">
                    <svg class="ninja-icon ninja-icon-xs me-2" fill="#dc3545">
                        <use href="#ninja-alert"></use>
                    </svg>
                    <strong class="me-auto">Erreur</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body"></div>
            </div>
        `;
        // Safely set the message content as text only
        toast.querySelector('.toast-body').textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Initialiser le gestionnaire de feedback
const ninjaFeedback = new NinjaFeedbackManager();

// Exposer globalement pour un accès facile
window.ninjaFeedback = ninjaFeedback;
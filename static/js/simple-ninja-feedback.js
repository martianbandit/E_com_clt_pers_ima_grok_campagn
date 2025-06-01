/**
 * Système de feedback ninja simple et autonome
 */

document.addEventListener('DOMContentLoaded', function() {
    // Créer le modal de feedback
    createFeedbackModal();
    
    // Attacher les événements aux boutons
    setupFeedbackButtons();
});

function createFeedbackModal() {
    const modalHTML = `
    <div class="modal fade" id="ninjaFeedbackModal" tabindex="-1" aria-labelledby="ninjaFeedbackModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content ninja-feedback-modal">
                <div class="modal-header ninja-feedback-header">
                    <h5 class="modal-title ninja-feedback-title" id="ninjaFeedbackModalLabel">
                        <svg class="ninja-icon ninja-icon-sm me-2" fill="#ffffff" width="20" height="20" viewBox="0 0 24 24">
                            <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
                            <circle cx="8" cy="10" r="1" fill="#ff6b35"/>
                            <circle cx="12" cy="10" r="1" fill="#ff6b35"/>
                            <circle cx="16" cy="10" r="1" fill="#ff6b35"/>
                        </svg>
                        <span id="feedbackModalTitle">Signaler un problème</span>
                    </h5>
                    <button type="button" class="btn-close ninja-btn-close" data-bs-dismiss="modal" aria-label="Fermer"></button>
                </div>
                <div class="modal-body ninja-feedback-body">
                    <form id="ninjaFeedbackForm" class="ninja-feedback-form">
                        <!-- Type de feedback -->
                        <div class="mb-3">
                            <label class="form-label ninja-form-label">Type de feedback</label>
                            <div class="ninja-feedback-types">
                                <div class="form-check ninja-form-check">
                                    <input class="form-check-input" type="radio" name="feedbackType" id="bugReport" value="bug" checked>
                                    <label class="form-check-label ninja-check-label" for="bugReport">
                                        ⚠️ Signaler un problème
                                    </label>
                                </div>
                                <div class="form-check ninja-form-check">
                                    <input class="form-check-input" type="radio" name="feedbackType" id="suggestion" value="suggestion">
                                    <label class="form-check-label ninja-check-label" for="suggestion">
                                        💡 Suggestion d'amélioration
                                    </label>
                                </div>
                                <div class="form-check ninja-form-check">
                                    <input class="form-check-input" type="radio" name="feedbackType" id="general" value="general">
                                    <label class="form-check-label ninja-check-label" for="general">
                                        💬 Commentaire général
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- Nom complet -->
                        <div class="mb-3">
                            <label for="feedbackName" class="form-label ninja-form-label">
                                👤 Nom complet <span class="text-danger">*</span>
                            </label>
                            <input type="text" class="form-control ninja-input" id="feedbackName" placeholder="Votre nom complet" required>
                        </div>

                        <!-- Email -->
                        <div class="mb-3">
                            <label for="feedbackEmail" class="form-label ninja-form-label">
                                📧 Adresse email <span class="text-danger">*</span>
                            </label>
                            <input type="email" class="form-control ninja-input" id="feedbackEmail" placeholder="votre@email.com" required>
                        </div>

                        <!-- Message -->
                        <div class="mb-3">
                            <label for="feedbackMessage" class="form-label ninja-form-label">
                                📝 <span id="feedbackMessageLabel">Décrivez le problème rencontré</span> <span class="text-danger">*</span>
                            </label>
                            <textarea class="form-control ninja-textarea" id="feedbackMessage" rows="4" placeholder="Décrivez en détail..." required></textarea>
                            <div class="form-text ninja-form-text">
                                Plus vous donnez de détails, plus notre équipe ninja pourra vous aider efficacement.
                            </div>
                        </div>

                        <!-- Informations système -->
                        <div class="ninja-system-info">
                            <small class="text-muted">
                                ℹ️ Les informations système seront incluses automatiquement pour faciliter le diagnostic.
                            </small>
                        </div>
                    </form>
                </div>
                <div class="modal-footer ninja-feedback-footer">
                    <button type="button" class="btn ninja-btn-secondary" data-bs-dismiss="modal">
                        ❌ Annuler
                    </button>
                    <button type="button" class="btn ninja-btn-primary" id="submitFeedbackBtn">
                        🚀 <span id="submitBtnText">Envoyer le rapport</span>
                    </button>
                </div>
            </div>
        </div>
    </div>`;

    // Ajouter le modal au body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Ajouter les styles CSS
    addFeedbackStyles();
}

function addFeedbackStyles() {
    const styles = `
    <style>
    .ninja-feedback-modal {
        border: none;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(255, 107, 53, 0.3);
        background: var(--bs-body-bg);
        overflow: hidden;
    }

    .ninja-feedback-header {
        background: linear-gradient(135deg, #ff6b35 0%, #e55528 100%);
        color: white;
        border-radius: 15px 15px 0 0;
        border: none;
        padding: 1.25rem 1.5rem;
        position: relative;
    }

    .ninja-feedback-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="ninja-pattern" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="10" cy="10" r="1" fill="rgba(255,255,255,0.1)"/></pattern></defs><rect width="100" height="100" fill="url(%23ninja-pattern)"/></svg>');
        opacity: 0.3;
    }

    .ninja-feedback-title {
        font-weight: 600;
        font-size: 1.1rem;
        margin: 0;
        display: flex;
        align-items: center;
        position: relative;
        z-index: 1;
    }

    .ninja-btn-close {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        padding: 0.5rem;
        opacity: 1;
        filter: brightness(0) invert(1);
        position: relative;
        z-index: 1;
        transition: all 0.3s ease;
    }

    .ninja-btn-close:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: scale(1.1) rotate(90deg);
    }

    .ninja-feedback-body {
        padding: 1.5rem;
        background: var(--bs-body-bg);
    }

    .ninja-feedback-types {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 1rem;
        background: rgba(255, 107, 53, 0.05);
        border-radius: 10px;
        border-left: 4px solid #ff6b35;
        margin-bottom: 1rem;
    }

    .ninja-form-check {
        margin: 0;
    }

    .ninja-check-label {
        display: flex;
        align-items: center;
        font-weight: 500;
        color: var(--bs-body-color);
        cursor: pointer;
        padding: 0.75rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }

    .ninja-check-label:hover {
        background: rgba(255, 107, 53, 0.1);
        transform: translateX(5px);
        border-color: rgba(255, 107, 53, 0.3);
    }

    .form-check-input:checked + .ninja-check-label {
        background: rgba(255, 107, 53, 0.15);
        color: #ff6b35;
        font-weight: 600;
        border-color: #ff6b35;
        box-shadow: 0 0 0 0.2rem rgba(255, 107, 53, 0.25);
    }

    .ninja-form-label {
        font-weight: 600;
        color: var(--bs-body-color);
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
        font-size: 0.95rem;
    }

    .ninja-input, .ninja-textarea {
        border: 2px solid #e9ecef;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        background: var(--bs-body-bg);
    }

    .ninja-input:focus, .ninja-textarea:focus {
        border-color: #ff6b35;
        box-shadow: 0 0 0 0.2rem rgba(255, 107, 53, 0.25);
        background: var(--bs-body-bg);
        transform: translateY(-1px);
    }

    .ninja-form-text {
        color: #6c757d;
        font-size: 0.875rem;
        margin-top: 0.5rem;
        font-style: italic;
    }

    .ninja-system-info {
        padding: 1rem;
        background: rgba(108, 117, 125, 0.1);
        border-radius: 8px;
        border-left: 3px solid #6c757d;
        margin-top: 1rem;
    }

    .ninja-feedback-footer {
        padding: 1rem 1.5rem;
        border: none;
        background: rgba(255, 107, 53, 0.02);
        display: flex;
        gap: 1rem;
    }

    .ninja-btn-primary {
        background: linear-gradient(135deg, #ff6b35 0%, #e55528 100%);
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: white;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        position: relative;
        overflow: hidden;
    }

    .ninja-btn-primary::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s ease;
    }

    .ninja-btn-primary:hover::before {
        left: 100%;
    }

    .ninja-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
        background: linear-gradient(135deg, #e55528 0%, #d44821 100%);
    }

    .ninja-btn-secondary {
        background: transparent;
        border: 2px solid #6c757d;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: #6c757d;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
    }

    .ninja-btn-secondary:hover {
        background: #6c757d;
        color: white;
        transform: translateY(-1px);
    }

    .ninja-btn-primary.loading {
        pointer-events: none;
        opacity: 0.7;
    }

    .ninja-btn-primary.loading::after {
        content: '';
        position: absolute;
        width: 16px;
        height: 16px;
        margin: auto;
        border: 2px solid transparent;
        border-top-color: #ffffff;
        border-radius: 50%;
        animation: ninja-spin 1s linear infinite;
    }

    @keyframes ninja-spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    /* Success state */
    .ninja-feedback-success {
        text-align: center;
        padding: 2rem;
    }

    .ninja-feedback-success h4 {
        color: #38a169;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    .ninja-feedback-success p {
        color: #6c757d;
        margin-bottom: 0;
    }

    /* Responsive */
    @media (max-width: 576px) {
        .ninja-feedback-types {
            flex-direction: column;
        }
        
        .ninja-feedback-header {
            padding: 1rem;
        }
        
        .ninja-feedback-body {
            padding: 1rem;
        }
        
        .ninja-feedback-footer {
            padding: 1rem;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .ninja-btn-primary, .ninja-btn-secondary {
            width: 100%;
            justify-content: center;
        }
    }
    </style>`;
    
    document.head.insertAdjacentHTML('beforeend', styles);
}

function setupFeedbackButtons() {
    // Chercher les boutons de feedback existants ou en créer
    const headerBtn = document.querySelector('[id*="feedback"], [class*="feedback"]') || createFeedbackButton('header');
    const footerBtn = document.querySelector('footer [id*="feedback"], footer [class*="feedback"]') || createFeedbackButton('footer');

    // Attacher les événements
    if (headerBtn) {
        headerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openFeedbackModal('bug');
        });
    }

    if (footerBtn) {
        footerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openFeedbackModal('suggestion');
        });
    }

    // Configuration du formulaire
    setupFormHandlers();
}

function createFeedbackButton(location) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn ninja-feedback-btn';
    button.innerHTML = `
        <svg class="ninja-icon ninja-icon-sm me-2" fill="currentColor" width="16" height="16" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
            <circle cx="8" cy="10" r="1" fill="#ff6b35"/>
            <circle cx="12" cy="10" r="1" fill="#ff6b35"/>
            <circle cx="16" cy="10" r="1" fill="#ff6b35"/>
        </svg>
        ${location === 'header' ? 'Feedback' : 'Nous contacter'}
    `;
    
    // Ajouter à l'emplacement approprié
    if (location === 'header') {
        const nav = document.querySelector('.navbar-nav');
        if (nav) {
            const li = document.createElement('li');
            li.className = 'nav-item';
            li.appendChild(button);
            nav.appendChild(li);
        }
    } else {
        const footer = document.querySelector('footer');
        if (footer) {
            footer.appendChild(button);
        }
    }
    
    return button;
}

function setupFormHandlers() {
    // Gestion du changement de type
    document.addEventListener('change', function(e) {
        if (e.target.name === 'feedbackType') {
            updateFormForType(e.target.value);
        }
    });

    // Gestion de la soumission
    document.addEventListener('click', function(e) {
        if (e.target.id === 'submitFeedbackBtn') {
            handleSubmit(e);
        }
    });
}

function openFeedbackModal(type = 'bug') {
    const modal = document.getElementById('ninjaFeedbackModal');
    if (!modal) return;

    // Réinitialiser le formulaire
    const form = document.getElementById('ninjaFeedbackForm');
    if (form) form.reset();

    // Définir le type par défaut
    const radioElement = document.getElementById(type === 'bug' ? 'bugReport' : 'suggestion');
    if (radioElement) {
        radioElement.checked = true;
        updateFormForType(type);
    }

    // Ouvrir le modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

function updateFormForType(type) {
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

async function handleSubmit(event) {
    event.preventDefault();
    
    if (!validateForm()) {
        return;
    }

    const submitBtn = document.getElementById('submitFeedbackBtn');
    const originalHTML = submitBtn.innerHTML;
    
    // État de chargement
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '🚀 Envoi en cours...';
    submitBtn.disabled = true;

    try {
        const feedbackData = collectFormData();
        await sendFeedback(feedbackData);
        
        // Succès
        showSuccessMessage();
        
    } catch (error) {
        console.error('Erreur lors de l\'envoi du feedback:', error);
        showErrorMessage('Une erreur est survenue lors de l\'envoi. Veuillez réessayer.');
    } finally {
        // Restaurer le bouton
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = originalHTML;
        submitBtn.disabled = false;
    }
}

function validateForm() {
    const name = document.getElementById('feedbackName').value.trim();
    const email = document.getElementById('feedbackEmail').value.trim();
    const message = document.getElementById('feedbackMessage').value.trim();
    
    if (!name) {
        alert('Le nom est requis');
        return false;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
        alert('Un email valide est requis');
        return false;
    }
    
    if (!message || message.length < 10) {
        alert('Le message doit contenir au moins 10 caractères');
        return false;
    }
    
    return true;
}

function collectFormData() {
    const feedbackType = document.querySelector('input[name="feedbackType"]:checked').value;
    
    return {
        type: feedbackType,
        name: document.getElementById('feedbackName').value.trim(),
        email: document.getElementById('feedbackEmail').value.trim(),
        message: document.getElementById('feedbackMessage').value.trim(),
        systemInfo: {
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            viewport: window.innerWidth + 'x' + window.innerHeight,
            language: navigator.language
        }
    };
}

async function sendFeedback(feedbackData) {
    const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackData)
    });

    if (!response.ok) {
        throw new Error('HTTP ' + response.status + ': ' + response.statusText);
    }

    return await response.json();
}

function showSuccessMessage() {
    const modalBody = document.querySelector('.ninja-feedback-body');
    modalBody.innerHTML = `
        <div class="ninja-feedback-success">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🥷✨</div>
            <h4>Merci pour votre retour !</h4>
            <p>Notre équipe ninja examine votre message et vous contactera si nécessaire.</p>
        </div>
    `;
    
    setTimeout(() => {
        const modal = bootstrap.Modal.getInstance(document.getElementById('ninjaFeedbackModal'));
        if (modal) modal.hide();
    }, 3000);
}

function showErrorMessage(message) {
    alert('Erreur: ' + message);
}
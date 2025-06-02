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
        <div class="modal-dialog modal-dialog-centered modal-sm">
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
        border-radius: 10px;
        box-shadow: 0 6px 20px rgba(255, 107, 53, 0.3);
        background: rgba(26, 26, 26, 0.97);
        backdrop-filter: blur(10px);
        overflow: hidden;
        max-width: 320px;
        width: 85vw;
        max-height: 60vh;
        border: 1px solid rgba(255, 107, 53, 0.4);
        display: flex;
        flex-direction: column;
    }

    .ninja-feedback-header {
        background: linear-gradient(135deg, #ff6b35 0%, #e55528 100%);
        color: white;
        border-radius: 10px 10px 0 0;
        border: none;
        padding: 0.4rem 0.6rem;
        position: relative;
        min-height: 36px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-shrink: 0;
        overflow: hidden;
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
        font-size: 0.85rem;
        margin: 0;
        display: flex;
        align-items: center;
        position: relative;
        z-index: 1;
        line-height: 1.2;
        flex: 1;
        letter-spacing: 0.3px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .ninja-btn-close {
        background: rgba(255, 255, 255, 0.25);
        border-radius: 50%;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 12px;
        font-weight: bold;
        transition: all 0.2s ease;
        width: 26px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        -webkit-tap-highlight-color: transparent;
    }

    .ninja-btn-close:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: scale(1.1) rotate(90deg);
    }

    .ninja-feedback-body {
        padding: 0.4rem 0.6rem;
        background: rgba(26, 26, 26, 0.95);
        max-height: 42vh;
        overflow-y: auto;
        flex: 1;
        color: #ffffff;
        font-size: 0.8rem;
        line-height: 1.3;
    }

    .ninja-feedback-types {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        padding: 0.25rem;
        background: rgba(255, 107, 53, 0.08);
        border-radius: 5px;
        border-left: 2px solid #ff6b35;
        margin-bottom: 0.3rem;
    }

    .ninja-form-check {
        margin: 0;
    }

    .ninja-check-label {
        display: flex;
        align-items: center;
        font-weight: 400;
        color: var(--bs-body-color);
        cursor: pointer;
        padding: 0.2rem 0.35rem;
        border-radius: 4px;
        transition: all 0.3s ease;
        border: 1px solid transparent;
        font-size: 0.7rem;
        min-height: 26px;
        max-height: 26px;
        line-height: 1.2;
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
        margin-bottom: 0.25rem;
        font-size: 0.8rem;
    }

    .ninja-input, .ninja-textarea {
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 0.4rem 0.6rem;
        font-size: 0.8rem;
        transition: all 0.3s ease;
        background: var(--bs-body-bg);
        margin-bottom: 0.3rem;
    }

    .ninja-input:focus, .ninja-textarea:focus {
        border-color: #ff6b35;
        box-shadow: 0 0 0 0.2rem rgba(255, 107, 53, 0.25);
        background: var(--bs-body-bg);
        transform: translateY(-1px);
    }

    .ninja-form-text {
        color: #6c757d;
        font-size: 0.75rem;
        margin-top: 0.2rem;
        font-style: italic;
    }

    .ninja-system-info {
        padding: 0.75rem;
        background: rgba(108, 117, 125, 0.1);
        border-radius: 6px;
        border-left: 2px solid #6c757d;
        margin-top: 0.75rem;
    }

    .ninja-feedback-footer {
        padding: 0.4rem;
        border: none;
        background: rgba(255, 107, 53, 0.05);
        display: flex;
        gap: 0.4rem;
        min-height: 32px;
        border-top: 1px solid rgba(255, 107, 53, 0.2);
    }

    .ninja-btn-primary {
        background: linear-gradient(135deg, #ff6b35 0%, #e55528 100%);
        border: none;
        border-radius: 4px;
        padding: 0.3rem 0.8rem;
        font-weight: 600;
        font-size: 0.75rem;
        min-height: 28px;
        max-height: 28px;
        line-height: 1;
        color: white;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        position: relative;
        overflow: hidden;
        font-size: 0.875rem;
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
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 4px;
        padding: 0.3rem 0.8rem;
        font-weight: 500;
        color: #ffffff;
        transition: all 0.3s ease;
        font-size: 0.75rem;
        min-height: 28px;
        max-height: 28px;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        -webkit-tap-highlight-color: transparent;
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

    /* Responsive - Mobile First */
    @media (max-width: 768px) {
        .modal-dialog {
            margin: 1rem 0.5rem;
            max-width: calc(100vw - 1rem);
        }
        
        .ninja-feedback-modal {
            border-radius: 8px;
            max-height: 80vh;
        }
        
        .ninja-feedback-header {
            padding: 0.75rem 1rem;
            border-radius: 8px 8px 0 0;
        }
        
        .ninja-feedback-title {
            font-size: 0.9rem;
        }
        
        .ninja-feedback-body {
            padding: 0.875rem;
            max-height: 50vh;
            overflow-y: auto;
        }
        
        .ninja-feedback-types {
            padding: 0.5rem;
            gap: 0.375rem;
        }
        
        .ninja-check-label {
            padding: 0.375rem 0.5rem;
            font-size: 0.8rem;
        }
        
        .ninja-form-label {
            font-size: 0.8rem;
            margin-bottom: 0.25rem;
        }
        
        .ninja-input, .ninja-textarea {
            padding: 0.5rem 0.625rem;
            font-size: 0.8rem;
            border-radius: 6px;
        }
        
        .ninja-textarea {
            rows: 2;
            min-height: 60px;
        }
        
        .ninja-form-text {
            font-size: 0.7rem;
            margin-top: 0.25rem;
        }
        
        .ninja-system-info {
            padding: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .ninja-system-info small {
            font-size: 0.65rem;
        }
        
        .ninja-feedback-footer {
            padding: 0.75rem;
            flex-direction: row;
            gap: 0.5rem;
        }
        
        .ninja-btn-primary, .ninja-btn-secondary {
            flex: 1;
            justify-content: center;
            padding: 0.5rem 0.75rem;
            font-size: 0.8rem;
            border-radius: 6px;
        }
        
        /* Touch-friendly interactions */
        .ninja-check-label {
            min-height: 44px;
            display: flex;
            align-items: center;
        }
        
        .form-check-input {
            min-width: 20px;
            min-height: 20px;
            margin-right: 0.75rem;
        }
        
        /* Improved focus states for mobile */
        .ninja-input:focus, .ninja-textarea:focus {
            transform: none;
            box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.3);
        }
        
        /* Better button hover states for touch */
        .ninja-btn-primary:active {
            transform: scale(0.98);
        }
        
        .ninja-btn-secondary:active {
            transform: scale(0.98);
        }
    }
    
    @media (max-width: 480px) {
        .modal-dialog {
            margin: 0.25rem;
            max-width: calc(100vw - 0.5rem);
        }
        
        .ninja-feedback-header {
            padding: 0.875rem 1rem;
        }
        
        .ninja-feedback-body {
            padding: 1rem;
        }
        
        .ninja-feedback-footer {
            padding: 0.875rem 1rem;
        }
        
        .ninja-feedback-types {
            padding: 0.625rem;
        }
        
        .ninja-check-label {
            font-size: 0.85rem;
            padding: 0.5rem;
        }
        
        .ninja-form-label {
            font-size: 0.85rem;
        }
        
        .ninja-input, .ninja-textarea {
            font-size: 0.85rem;
            padding: 0.5rem 0.75rem;
        }
        
        .ninja-btn-primary, .ninja-btn-secondary {
            padding: 0.75rem 1rem;
            font-size: 0.9rem;
        }
    }
    
    /* Landscape phone optimizations */
    @media (max-height: 500px) and (orientation: landscape) {
        .ninja-feedback-body {
            max-height: 60vh;
            padding: 0.75rem;
        }
        
        .ninja-feedback-types {
            flex-direction: row;
            flex-wrap: wrap;
            justify-content: space-between;
        }
        
        .ninja-form-check {
            flex: 1;
            min-width: 150px;
        }
        
        .ninja-textarea {
            rows: 2;
            min-height: 60px;
        }
        
        .ninja-feedback-footer {
            flex-direction: row;
            gap: 1rem;
        }
        
        .ninja-btn-primary, .ninja-btn-secondary {
            width: auto;
            flex: 1;
        }
    }
    
    /* Styles pour le bouton de feedback du header */
    .ninja-header-feedback-btn {
        background: transparent !important;
        border: 2px solid #ff6b35 !important;
        color: #ff6b35 !important;
        transition: all 0.3s ease !important;
    }
    
    .ninja-header-feedback-btn:hover,
    .ninja-header-feedback-btn:focus {
        background: #ff6b35 !important;
        border-color: #ff6b35 !important;
        color: white !important;
        box-shadow: 0 0 0 0.2rem rgba(255, 107, 53, 0.25) !important;
        transform: translateY(-1px) !important;
    }
    
    .ninja-header-feedback-btn:active {
        background: #e55528 !important;
        border-color: #e55528 !important;
        transform: translateY(0) !important;
    }
    
    /* Mode sombre */
    [data-bs-theme="dark"] .ninja-header-feedback-btn {
        color: #ff6b35 !important;
        border-color: #ff6b35 !important;
    }
    
    [data-bs-theme="dark"] .ninja-header-feedback-btn:hover,
    [data-bs-theme="dark"] .ninja-header-feedback-btn:focus {
        background: #ff6b35 !important;
        color: white !important;
    }
    
    /* Mode clair */
    [data-bs-theme="light"] .ninja-header-feedback-btn {
        color: #ff6b35 !important;
        border-color: #ff6b35 !important;
    }
    
    [data-bs-theme="light"] .ninja-header-feedback-btn:hover,
    [data-bs-theme="light"] .ninja-header-feedback-btn:focus {
        background: #ff6b35 !important;
        color: white !important;
    }
    </style>`;
    
    document.head.insertAdjacentHTML('beforeend', styles);
}

function setupFeedbackButtons() {
    // Chercher les boutons de feedback existants ou en créer
    const headerBtn = document.querySelector('[id*="feedback"], [class*="feedback"]') || createFeedbackButton('header');
    const footerBtn = document.querySelector('footer [id*="feedback"], footer [class*="feedback"]') || createFeedbackButton('footer');

    // Attacher les événements avec support tactile
    if (headerBtn) {
        headerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openFeedbackModal('bug');
        });
        
        // Support tactile amélioré
        headerBtn.addEventListener('touchstart', (e) => {
            headerBtn.style.transform = 'scale(0.95)';
        });
        
        headerBtn.addEventListener('touchend', (e) => {
            headerBtn.style.transform = '';
        });
    }

    if (footerBtn) {
        footerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openFeedbackModal('suggestion');
        });
        
        // Support tactile amélioré
        footerBtn.addEventListener('touchstart', (e) => {
            footerBtn.style.transform = 'scale(0.95)';
        });
        
        footerBtn.addEventListener('touchend', (e) => {
            footerBtn.style.transform = '';
        });
    }

    // Configuration du formulaire
    setupFormHandlers();
    
    // Créer le bouton flottanttant pour mobile
    createFloatingFeedbackButton();
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

function createFloatingFeedbackButton() {
    // Créer un bouton flottant pour mobile
    const floatingBtn = document.createElement('button');
    floatingBtn.type = 'button';
    floatingBtn.id = 'floating-feedback-btn';
    floatingBtn.className = 'ninja-floating-feedback';
    floatingBtn.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#ffffff">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
            <circle cx="8" cy="10" r="1.5" fill="#ffffff"/>
            <circle cx="12" cy="10" r="1.5" fill="#ffffff"/>
            <circle cx="16" cy="10" r="1.5" fill="#ffffff"/>
        </svg>
    `;
    
    // Styles pour le bouton flottant
    const floatingStyles = `
    <style>
    .ninja-floating-feedback {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff6b35 0%, #e55528 100%);
        border: 2px solid #ff6b35;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .ninja-floating-feedback:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6);
        background: linear-gradient(135deg, #e55528 0%, #d44821 100%);1 100%);
    }
    
    .ninja-floating-feedback:active {
        transform: scale(0.95);
    }
    
    /* Masquer sur desktop */
    @media (min-width: 768px) {
        .ninja-floating-feedback {
            display: none;
        }
    }
    
    /* Animation d'apparition */
    @keyframes ninja-float-in {
        from {
            transform: scale(0) rotate(180deg);
            opacity: 0;
        }
        to {
            transform: scale(1) rotate(0deg);
            opacity: 1;
        }
    }
    
    .ninja-floating-feedback {
        animation: ninja-float-in 0.5s ease-out;
    }
    </style>`;
    
    document.head.insertAdjacentHTML('beforeend', floatingStyles);
    document.body.appendChild(floatingBtn);
    
    // Événement de clic
    floatingBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openFeedbackModal('bug');
    });
    
    // Support tactile amélioré
    floatingBtn.addEventListener('touchstart', (e) => {
        floatingBtn.style.transform = 'scale(0.9)';
    });
    
    floatingBtn.addEventListener('touchend', (e) => {
        floatingBtn.style.transform = '';
    });
    
    return floatingBtn;
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
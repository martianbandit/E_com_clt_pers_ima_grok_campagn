/**
 * Sentry Frontend Monitoring Initialization for NinjaLead.ai
 * Monitoring des erreurs et performances côté client
 */

// Configuration Sentry pour le frontend
(function() {
    // Vérifier si Sentry est déjà chargé
    if (window.Sentry) {
        return;
    }

    // Configuration Sentry
    const sentryConfig = {
        dsn: "https://350994d4ed87e5e65b314481f8257c07@o4509423969107968.ingest.us.sentry.io/4509424027303936",
        
        // Données PII pour un meilleur debugging
        sendDefaultPii: true,
        
        // Monitoring de performance complet
        tracesSampleRate: 1.0,
        profilesSampleRate: 1.0,
        
        // Environnement et release
        environment: window.location.hostname.includes('localhost') ? 'development' : 'production',
        release: "ninjaleads@1.0.0",
        
        // Intégrations spécialisées
        integrations: [
            // Performance et navigation
            new Sentry.BrowserTracing({
                enableLongTask: true,
                enableInp: true,
                tracingOrigins: [window.location.hostname, /^\//],
            }),
            
            // Session replay pour debugging
            new Sentry.Replay({
                maskAllText: false,
                blockAllMedia: false,
                sampleRate: 0.1,
                errorSampleRate: 1.0,
            }),
            
            // Feedback utilisateur
            new Sentry.Feedback({
                colorScheme: "system",
                isEmailRequired: true,
                showBranding: false,
                formTitle: "Signaler un problème",
                submitButtonLabel: "Envoyer le rapport",
                messageLabel: "Décrivez le problème rencontré",
                emailLabel: "Votre adresse email",
                nameLabel: "Votre nom (optionnel)",
                successMessageText: "Merci pour votre retour !",
            }),
        ],
        
        // Filtrage des erreurs non critiques
        beforeSend(event, hint) {
            const error = hint.originalException;
            if (error && error.message) {
                // Ignorer les erreurs réseau communes
                if (error.message.includes('Network request failed') ||
                    error.message.includes('Failed to fetch') ||
                    error.message.includes('Load failed')) {
                    return null;
                }
                
                // Ignorer les erreurs de scripts externes
                if (error.message.includes('Script error')) {
                    return null;
                }
            }
            return event;
        },
        
        // Tags personnalisés
        initialScope: {
            tags: {
                component: "frontend",
                platform: "web",
                app: "ninjaleads",
            },
        },
    };

    // Initialisation avec gestion d'erreur
    try {
        Sentry.init(sentryConfig);
        
        // Configuration du contexte utilisateur si disponible
        if (window.currentUser) {
            Sentry.setUser({
                id: window.currentUser.id,
                email: window.currentUser.email,
                username: window.currentUser.username,
            });
        }
        
        // Ajout du contexte de l'application
        Sentry.setContext("application", {
            name: "NinjaLead.ai",
            version: "1.0.0",
            component: "frontend",
        });
        
        console.log("✅ Sentry monitoring initialized for frontend");
        
    } catch (error) {
        console.warn("❌ Failed to initialize Sentry:", error);
    }

    // Fonction globale pour capturer des événements personnalisés
    window.captureSentryEvent = function(message, level = 'info', extra = {}) {
        try {
            Sentry.captureMessage(message, level);
            if (Object.keys(extra).length > 0) {
                Sentry.setExtra('customData', extra);
            }
        } catch (error) {
            console.warn("Failed to capture Sentry event:", error);
        }
    };

    // Fonction pour mettre à jour le contexte utilisateur
    window.updateSentryUser = function(userData) {
        try {
            Sentry.setUser({
                id: userData.id,
                email: userData.email,
                username: userData.username,
            });
        } catch (error) {
            console.warn("Failed to update Sentry user:", error);
        }
    };

    // Monitoring automatique des erreurs JavaScript non gérées
    window.addEventListener('error', function(event) {
        if (window.Sentry && event.error) {
            Sentry.captureException(event.error);
        }
    });

    // Monitoring des promesses rejetées non gérées
    window.addEventListener('unhandledrejection', function(event) {
        if (window.Sentry) {
            Sentry.captureException(event.reason);
        }
    });

    // Monitoring des performances de navigation
    if ('performance' in window && 'getEntriesByType' in window.performance) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const navigation = performance.getEntriesByType('navigation')[0];
                if (navigation && window.Sentry) {
                    Sentry.setContext("performance", {
                        loadTime: Math.round(navigation.loadEventEnd - navigation.fetchStart),
                        domContentLoaded: Math.round(navigation.domContentLoadedEventEnd - navigation.fetchStart),
                        firstPaint: Math.round(navigation.responseStart - navigation.fetchStart),
                    });
                }
            }, 1000);
        });
    }

})();
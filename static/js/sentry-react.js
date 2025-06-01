/**
 * Sentry React Integration for NinjaLead.ai
 * Advanced monitoring with feedback integration
 */

// Import Sentry for React
import * as Sentry from "@sentry/react";

// Initialize Sentry with advanced configuration
Sentry.init({
  dsn: "https://350994d4ed87e5e65b314481f8257c07@o4509423969107968.ingest.us.sentry.io/4509424027303936",
  
  // Setting this option to true will send default PII data to Sentry.
  // For example, automatic IP address collection on events
  sendDefaultPii: true,
  
  // Advanced performance monitoring
  tracesSampleRate: 1.0,
  profilesSampleRate: 1.0,
  
  // Environment and release tracking
  environment: window.location.hostname.includes('localhost') ? 'development' : 'production',
  release: "ninjaleads@1.0.0",
  
  // Enhanced integrations
  integrations: [
    // User feedback integration with customization
    Sentry.feedbackIntegration({
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
    
    // Browser performance tracking
    Sentry.browserTracingIntegration({
      // Track all navigation and interactions
      enableLongTask: true,
      enableInp: true,
    }),
    
    // Enhanced replay for debugging
    Sentry.replayIntegration({
      maskAllText: false,
      blockAllMedia: false,
    }),
  ],
  
  // Session replay sampling
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  
  // Enhanced error filtering
  beforeSend(event, hint) {
    // Filter out common browser errors that aren't actionable
    const error = hint.originalException;
    if (error && error.message) {
      // Skip network errors that aren't under our control
      if (error.message.includes('Network request failed') ||
          error.message.includes('Failed to fetch')) {
        return null;
      }
    }
    return event;
  },
  
  // Custom tags for better organization
  initialScope: {
    tags: {
      component: "frontend",
      platform: "web",
    },
    user: {
      // Will be populated dynamically based on authenticated user
    },
  },
});

// Custom error boundary for React components
export const SentryErrorBoundary = Sentry.withErrorBoundary;

// Custom hooks for performance monitoring
export const useSentryTransaction = (name, op = 'navigation') => {
  return Sentry.startTransaction({ name, op });
};

// Function to set user context
export const setSentryUser = (userData) => {
  Sentry.setUser({
    id: userData.id,
    email: userData.email,
    username: userData.username,
  });
};

// Function to add custom context
export const addSentryContext = (key, data) => {
  Sentry.setContext(key, data);
};

// Function to capture custom events
export const captureSentryEvent = (message, level = 'info', extra = {}) => {
  Sentry.captureMessage(message, level);
  if (Object.keys(extra).length > 0) {
    Sentry.setExtra('additionalData', extra);
  }
};

// Export Sentry for direct usage
export { Sentry };
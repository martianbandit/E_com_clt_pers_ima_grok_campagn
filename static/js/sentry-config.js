import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: "https://350994d4ed87e5e65b314481f8257c07@o4509423969107968.ingest.us.sentry.io/4509424027303936",
  // Setting this option to true will send default PII data to Sentry.
  // For example, automatic IP address collection on events
  sendDefaultPii: true,
  integrations: [
    Sentry.feedbackIntegration({
      colorScheme: "system",
      isNameRequired: true,
      isEmailRequired: true,
    }),
  ]
});
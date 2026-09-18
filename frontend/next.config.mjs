import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    // Requis par Next.js 14 pour que `instrumentation.ts` soit chargé.
    instrumentationHook: true,
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
};

/**
 * L'enrobage Sentry n'est appliqué que si un DSN est configuré au moment du
 * build : une installation sans suivi d'erreurs se construit exactement comme
 * avant, sans greffon supplémentaire ni téléversement de sources.
 */
export default process.env.NEXT_PUBLIC_SENTRY_DSN
  ? withSentryConfig(nextConfig, {
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      // Sans jeton, les sources ne sont pas téléversées : les piles d'appels
      // restent minifiées, mais le build n'échoue pas pour autant.
      authToken: process.env.SENTRY_AUTH_TOKEN,
      silent: true,
      // Le greffon retire les fichiers de sources du serveur après envoi :
      // ils ne doivent pas rester servables publiquement.
      widenClientFileUpload: false,
      disableLogger: true,
    })
  : nextConfig;

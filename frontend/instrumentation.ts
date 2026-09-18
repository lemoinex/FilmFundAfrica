/**
 * Point d'entrée d'instrumentation de Next.js : il choisit la configuration
 * correspondant au runtime qui démarre. Activé par `instrumentationHook`
 * dans `next.config.mjs`.
 */
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

export { captureRequestError as onRequestError } from "@sentry/nextjs";

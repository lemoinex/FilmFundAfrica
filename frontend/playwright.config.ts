import { defineConfig, devices } from "@playwright/test";

/**
 * Tests de bout en bout : un vrai navigateur, une vraie API, une base neuve.
 *
 * Playwright démarre lui-même les deux serveurs. `reuseExistingServer` permet
 * de garder une pile déjà lancée pendant le développement, au lieu d'en
 * relancer une à chaque exécution.
 */
const API_PORT = process.env.E2E_API_PORT ?? "8010";
const WEB_PORT = process.env.E2E_WEB_PORT ?? "3100";

export const API_URL = `http://127.0.0.1:${API_PORT}`;
const WEB_URL = `http://127.0.0.1:${WEB_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  // Les tests partagent une seule base : les faire tourner en parallèle
  // rendrait leurs échecs difficiles à lire pour un gain de quelques secondes.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: WEB_URL,
    locale: "fr-FR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Permet de pointer un binaire déjà présent (image CI, bac à sable) sans
    // toucher au reste de la configuration.
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }
      : {},
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: [
    {
      command: "bash ../scripts/e2e-api.sh",
      url: `${API_URL}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: { E2E_API_PORT: API_PORT, E2E_WEB_PORT: WEB_PORT },
    },
    {
      // `NEXT_PUBLIC_*` est figé à la compilation : la variable doit être dans
      // l'environnement de la commande elle-même, pas seulement dans celui de
      // Playwright, sinon le navigateur appellerait l'API par défaut.
      command: `NEXT_PUBLIC_API_URL=${API_URL} npm run dev -- --port ${WEB_PORT}`,
      url: WEB_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { NEXT_PUBLIC_API_URL: API_URL },
    },
  ],
});

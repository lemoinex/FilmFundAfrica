import { expect, test } from "@playwright/test";

import { createProject, freshEmail, registerAndVerify } from "./helpers";

test.describe("AI Writer", () => {
  // Le fournisseur `mock` répond immédiatement, mais la génération passe par
  // une tâche : le test attend un résultat, pas une réponse HTTP.
  test("générer un document, puis l'ouvrir dans l'éditeur", async ({ page }) => {
    await registerAndVerify(page, freshEmail("writer"));
    const projectId = await createProject(page, "Projet à rédiger");

    await page.goto(`/projets/${projectId}/ai-writer`);
    await expect(page.getByRole("heading", { name: "AI Writer" })).toBeVisible();

    await page.getByRole("button", { name: /^Générer$/ }).click();

    const result = page.getByRole("heading", { name: "Document généré" });
    await expect(result).toBeVisible({ timeout: 45_000 });
    // Le fournisseur `mock` s'annonce comme tel : le document ne prétend pas
    // être rédigé par une IA.
    await expect(page.getByText(/Aucun fournisseur d'IA configuré/i)).toBeVisible();

    await page.getByRole("link", { name: "Éditer" }).click();
    await expect(page).toHaveURL(/\/documents\//);

    // L'éditeur ouvre en aperçu : le document rédigé doit s'y lire, titré avec
    // le vrai nom du projet (un test de ce fichier a révélé qu'il affichait
    // « Projet sans titre »).
    await expect(
      page.getByRole("heading", { name: /Projet à rédiger/ }).first(),
    ).toBeVisible();
    // …et se retrouver tel quel dans le champ d'édition.
    await page.getByRole("button", { name: "Éditer" }).click();
    await expect(page.getByLabel("Contenu du document")).not.toBeEmpty();
  });

  test("le crédit consommé bloque la génération suivante, avec un message clair", async ({
    page,
  }) => {
    await registerAndVerify(page, freshEmail("credits"));
    const projectId = await createProject(page, "Projet à un crédit");

    await page.goto(`/projets/${projectId}/ai-writer`);
    await page.getByRole("button", { name: /^Générer$/ }).click();
    await expect(page.getByRole("heading", { name: "Document généré" })).toBeVisible({
      timeout: 45_000,
    });

    // L'offre gratuite accorde un seul crédit.
    await page.getByRole("button", { name: /Régénérer/ }).click();
    await expect(page.getByText(/Crédits IA épuisés|insuffisants/i)).toBeVisible({
      timeout: 30_000,
    });
  });

  // Le défaut corrigé : le frontend imposait `language: "fr"` à chaque appel,
  // si bien qu'un dossier anglais recevait des documents français.
  test("la langue du document est proposée d'après l'interface, et reste modifiable", async ({
    page,
  }) => {
    await registerAndVerify(page, freshEmail("langue-doc"));
    const projectId = await createProject(page, "Projet bilingue");

    await page.goto(`/projets/${projectId}/ai-writer`);
    const french = page.getByRole("button", { name: "Français", exact: true });
    const english = page.getByRole("button", { name: "English", exact: true });

    // L'interface est en français : c'est la langue proposée par défaut.
    await expect(french).toHaveAttribute("aria-pressed", "true");
    await expect(english).toHaveAttribute("aria-pressed", "false");

    await english.click();
    await expect(english).toHaveAttribute("aria-pressed", "true");

    await page.getByRole("button", { name: /^Générer$/ }).click();
    await expect(page.getByRole("heading", { name: "Document généré" })).toBeVisible({
      timeout: 45_000,
    });
  });
});

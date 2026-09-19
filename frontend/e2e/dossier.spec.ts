import { expect, test } from "@playwright/test";

import { createProject, freshEmail, registerAndVerify } from "./helpers";

/**
 * La chaîne d'agents vue depuis l'interface. Le fournisseur `mock` déroule les
 * huit étapes sans clé API, mais ne rend jamais un dossier exportable : c'est
 * précisément ce que l'écran doit dire, plutôt que de laisser croire à une
 * validation.
 */
test.describe("Dossier de financement", () => {
  test("un projet neuf annonce que la chaîne n'a jamais tourné", async ({ page }) => {
    await registerAndVerify(page, freshEmail("dossier"));
    const projectId = await createProject(page, "Projet à monter");

    await page.goto(`/projets/${projectId}/dossier`);
    await expect(
      page.getByRole("heading", { name: "Dossier de financement" }),
    ).toBeVisible();
    await expect(page.getByText(/n'a jamais tourné/)).toBeVisible();

    // Le coût est annoncé avant de lancer, pas découvert après.
    await expect(page.getByText("8 crédits")).toBeVisible();
  });

  test("l'offre gratuite ne peut pas payer une chaîne, et le dit", async ({ page }) => {
    // Un crédit pour huit agents : le refus doit être lisible, pas un plantage.
    await registerAndVerify(page, freshEmail("dossier-gratuit"));
    const projectId = await createProject(page, "Projet sans crédits");

    await page.goto(`/projets/${projectId}/dossier`);
    await page.getByRole("button", { name: /Lancer la chaîne/ }).click();

    await expect(page.getByRole("alert").first()).toBeVisible({ timeout: 30_000 });
    // Le dossier n'a pas bougé : aucun passage n'a été facturé.
    await expect(page.getByText(/n'a jamais tourné/)).toBeVisible();
  });

  test("on accède au dossier depuis la fiche projet", async ({ page }) => {
    await registerAndVerify(page, freshEmail("dossier-nav"));
    const projectId = await createProject(page, "Projet navigable");

    await page.goto(`/projets/${projectId}`);
    await page.getByRole("link", { name: "Dossier de financement" }).click();

    await expect(page).toHaveURL(new RegExp(`/projets/${projectId}/dossier`));
    await expect(
      page.getByRole("heading", { name: "Dossier de financement" }),
    ).toBeVisible();
  });
});

import { expect, test } from "@playwright/test";

import { createProject, freshEmail, registerAndVerify } from "./helpers";

test.describe("Projets", () => {
  test("créer un projet le fait apparaître dans la liste avec son score", async ({ page }) => {
    await registerAndVerify(page, freshEmail("projet"));
    await createProject(page, "Les Gardiennes du fleuve");

    await expect(page.getByRole("heading", { name: "Les Gardiennes du fleuve" })).toBeVisible();

    await page.goto("/projets");
    await expect(page.getByText("Les Gardiennes du fleuve")).toBeVisible();
  });

  test("l'offre gratuite est limitée à un projet, et le dit", async ({ page }) => {
    await registerAndVerify(page, freshEmail("quota"));
    await createProject(page, "Premier projet");

    await page.goto("/projets/nouveau");
    await page.getByLabel(/Titre du projet/).fill("Deuxième projet");
    await page.getByRole("button", { name: "Étape 7 : Public cible" }).click();
    await page.getByRole("button", { name: "Créer mon projet" }).click();

    // Le refus est explicite : l'auteur comprend que c'est une limite d'offre.
    await expect(page.getByText(/offre|limitée|projet\(s\)/i).first()).toBeVisible();
    await expect(page).toHaveURL(/projets\/nouveau/);
  });
});

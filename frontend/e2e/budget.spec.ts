import { expect, test } from "@playwright/test";

import { createProject, freshEmail, registerAndVerify } from "./helpers";

test.describe("Budget et plan de financement", () => {
  test("installer la trame, chiffrer un poste, voir le total suivre", async ({ page }) => {
    await registerAndVerify(page, freshEmail("budget"));
    const projectId = await createProject(page, "Projet à chiffrer");

    await page.goto(`/projets/${projectId}/budget`);
    await expect(page.getByRole("heading", { name: "Budget et financement" })).toBeVisible();
    await expect(page.getByText("Budget vide")).toBeVisible();

    await page.getByRole("button", { name: "Installer la trame" }).click();

    // La trame propose des postes, et aucun montant : c'est la règle du module.
    const total = page.getByText(/^0 XAF$/).first();
    await expect(total).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Écriture et scénario")).toBeVisible();

    const price = page.getByLabel("Prix unitaire — Écriture et scénario");
    await price.fill("2000000");
    await price.blur();

    // Le montant n'est jamais saisi : il descend du serveur.
    await expect(page.getByText("2 000 000 XAF").first()).toBeVisible({ timeout: 20_000 });
  });

  test("une source espérée ne compte pas comme acquise", async ({ page }) => {
    await registerAndVerify(page, freshEmail("plan"));
    const projectId = await createProject(page, "Projet à financer");

    await page.goto(`/projets/${projectId}/budget`);
    await page.getByRole("button", { name: "Installer la trame" }).click();
    const price = page.getByLabel("Prix unitaire — Écriture et scénario");
    await expect(price).toBeVisible({ timeout: 20_000 });
    await price.fill("1000000");
    await price.blur();
    await expect(page.getByText("1 000 000 XAF").first()).toBeVisible({ timeout: 20_000 });

    await page.getByLabel("Ajouter une source").fill("Coproducteur pressenti");
    await page.getByLabel("Montant de la source").fill("500000");
    await page.getByRole("button", { name: "Ajouter" }).last().click();

    // Tant qu'elle n'est pas cochée « Acquis », la couverture reste à zéro.
    await expect(page.getByText("0 % du budget est acquis.")).toBeVisible({ timeout: 20_000 });

    // `check()` exigerait que la case bascule instantanément ; ici son état
    // vient du serveur, et c'est le chiffre affiché qui fait foi.
    await page.getByRole("checkbox").first().click();
    await expect(page.getByText("50 % du budget est acquis.")).toBeVisible({ timeout: 20_000 });
  });
});

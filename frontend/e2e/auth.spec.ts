import { expect, test } from "@playwright/test";

import { freshEmail, PASSWORD, registerAndVerify } from "./helpers";

test.describe("Inscription et connexion", () => {
  test("une inscription confirmée ouvre la session", async ({ page }) => {
    await registerAndVerify(page, freshEmail("parcours"));
    await expect(page.getByRole("heading", { name: /Bienvenue/i })).toBeVisible();
  });

  test("l'inscription répond la même chose sur une adresse déjà prise", async ({ page }) => {
    const email = freshEmail("occupee");
    await registerAndVerify(page, email);

    // Un tiers tente de s'inscrire avec la même adresse : l'écran doit être
    // identique, sans quoi il apprendrait que cette personne est inscrite.
    await page.goto("/inscription");
    await page.getByLabel("Prénom").fill("Intrus");
    await page.getByLabel("Nom", { exact: true }).fill("Inconnu");
    await page.getByLabel("Adresse e-mail").fill(email);
    await page.getByLabel("Mot de passe").fill("AutreMotDePasse1");
    await page.getByRole("button", { name: "Créer mon compte" }).click();

    await expect(page.getByRole("heading", { name: "Vérifiez votre boîte mail" })).toBeVisible();
    await expect(page.getByText(/déjà|existe|pris/i)).toHaveCount(0);
  });

  test("un compte non confirmé ne peut pas se connecter, et peut redemander le lien", async ({
    page,
  }) => {
    const email = freshEmail("non-confirme");

    await page.goto("/inscription");
    await page.getByLabel("Prénom").fill("Awa");
    await page.getByLabel("Nom", { exact: true }).fill("Diop");
    await page.getByLabel("Adresse e-mail").fill(email);
    await page.getByLabel("Mot de passe").fill(PASSWORD);
    await page.getByRole("button", { name: "Créer mon compte" }).click();
    await expect(page.getByRole("heading", { name: "Vérifiez votre boîte mail" })).toBeVisible();

    await page.goto("/connexion");
    await page.getByLabel("Adresse e-mail").fill(email);
    await page.getByLabel("Mot de passe").fill(PASSWORD);
    await page.getByRole("button", { name: "Se connecter" }).click();

    await expect(page.getByText(/Adresse non confirmée/i)).toBeVisible();
    const resend = page.getByRole("button", { name: /Renvoyer le lien/i });
    await expect(resend).toBeVisible();
    await resend.click();
    await expect(page.getByText(/un nouveau vient de partir/i)).toBeVisible();
  });

  test("un mot de passe erroné ne dit pas si le compte existe", async ({ page }) => {
    const email = freshEmail("mauvais-mdp");
    await registerAndVerify(page, email);

    await page.goto("/connexion");
    await page.getByLabel("Adresse e-mail").fill(email);
    await page.getByLabel("Mot de passe").fill("MauvaisMotDePasse1");
    await page.getByRole("button", { name: "Se connecter" }).click();
    const known = await page.getByRole("alert").first().innerText();

    await page.goto("/connexion");
    await page.getByLabel("Adresse e-mail").fill(freshEmail("jamais-vu"));
    await page.getByLabel("Mot de passe").fill("MauvaisMotDePasse1");
    await page.getByRole("button", { name: "Se connecter" }).click();
    const unknown = await page.getByRole("alert").first().innerText();

    expect(known).toBe(unknown);
  });

  test("un lien de confirmation déjà utilisé est refusé proprement", async ({ page }) => {
    await page.goto("/verifier-email?token=jeton-invalide-et-inexistant");
    await expect(page.getByRole("heading", { name: /Confirmation impossible/i })).toBeVisible();
  });
});

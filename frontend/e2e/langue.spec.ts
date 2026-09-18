import { expect, test } from "@playwright/test";

import { freshEmail, registerAndVerify } from "./helpers";

/**
 * L'internationalisation ne se vérifie qu'en la traversant : un catalogue
 * complet ne dit rien de la page réellement servie. Ces tests contrôlent les
 * trois points où elle peut échouer sans se voir — le rendu serveur, la
 * persistance entre deux pages, et l'accord grammatical.
 */
test.describe("Langue de l'interface", () => {
  test("la page publique s'affiche en anglais et le déclare à `<html lang>`", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "fr");
    await expect(page.getByRole("link", { name: "Connexion" })).toBeVisible();

    await page.getByLabel("Changer de langue").first().selectOption("en");

    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("le choix survit à un rechargement, dès le rendu serveur", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Changer de langue").first().selectOption("en");
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();

    // Rendu serveur : le cookie doit suffire, sans attendre l'hydratation.
    await page.goto("/connexion");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  test("la langue suit le compte, et les accords suivent la langue", async ({ page }) => {
    await registerAndVerify(page, freshEmail("langue"));
    await expect(page.getByRole("heading", { name: /Bienvenue/i })).toBeVisible();

    await page.getByLabel("Changer de langue").first().selectOption("en");
    await expect(page.getByRole("heading", { name: /Welcome/i })).toBeVisible();

    // Un compte neuf a exactement 1 crédit : le singulier anglais doit être
    // choisi par la règle de la langue, pas par une comparaison `> 1`.
    await page.goto("/abonnement");
    await expect(page.getByText("1 AI credit left")).toBeVisible();

    // La préférence est enregistrée sur le profil : elle revient après une
    // nouvelle session, cookie effacé.
    await page.context().clearCookies();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Subscription" })).toBeVisible();
  });
});

test.describe("Messages de l'API", () => {
  test("une erreur du serveur arrive dans la langue choisie dans l'interface", async ({
    page,
  }) => {
    // Le navigateur des tests annonce l'anglais ; on choisit le français dans
    // l'interface pour vérifier que c'est bien ce choix-là qui l'emporte.
    await page.goto("/connexion");
    await page.getByLabel("Changer de langue").first().selectOption("fr");

    await page.getByLabel("Adresse e-mail").fill("inconnu@example.com");
    await page.getByLabel("Mot de passe").fill("MotDePasse123");
    await page.getByRole("button", { name: "Se connecter" }).click();

    // `.first()` : Next.js ajoute son propre `role="alert"` pour annoncer les
    // changements de route, et la recherche serait ambiguë sans cela.
    const alert = page.getByRole("alert").first();
    await expect(alert).toHaveText("Adresse e-mail ou mot de passe incorrect.");

    await page.getByLabel("Changer de langue").first().selectOption("en");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(alert).toHaveText("Incorrect email address or password.");
  });
});

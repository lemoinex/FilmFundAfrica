import { expect, type Page, type Response } from "@playwright/test";

/**
 * Une adresse neuve par test : la base est partagée, les comptes ne le sont pas.
 *
 * `example.com` et non `example.test` : les domaines à usage spécial sont
 * refusés par la validation d'adresse du backend.
 */
export function freshEmail(prefix: string): string {
  return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 10000)}@example.com`;
}

export const PASSWORD = "MotDePasse123";

/**
 * Inscrit un compte par l'interface et ouvre le lien de confirmation.
 *
 * Le jeton n'est jamais affiché : il voyage dans la réponse de `/register`,
 * que l'API ne renseigne qu'en environnement `development`. On l'intercepte
 * comme le ferait la boîte mail du destinataire.
 */
export async function registerAndVerify(page: Page, email: string): Promise<void> {
  const registration = page.waitForResponse(
    (response: Response) =>
      response.url().includes("/api/v1/auth/register") && response.request().method() === "POST",
  );

  await page.goto("/inscription");
  await page.getByLabel("Prénom").fill("Awa");
  await page.getByLabel("Nom", { exact: true }).fill("Diop");
  await page.getByLabel("Adresse e-mail").fill(email);
  await page.getByLabel("Mot de passe").fill(PASSWORD);
  await page.getByRole("button", { name: "Créer mon compte" }).click();

  const body = await (await registration).json();
  await expect(page.getByRole("heading", { name: "Vérifiez votre boîte mail" })).toBeVisible();

  const token = body.detail.split("Jeton : ")[1]?.trim();
  expect(token, "l'API de développement doit renvoyer le jeton de confirmation").toBeTruthy();

  await page.goto(`/verifier-email?token=${token}`);
  await expect(page).toHaveURL(/tableau-de-bord/);
}

/**
 * Crée un projet par l'assistant et renvoie son identifiant.
 *
 * Seul le titre est obligatoire : on passe par le sommaire des étapes plutôt
 * que d'enchaîner sept clics sur « Continuer ».
 */
export async function createProject(page: Page, title: string): Promise<string> {
  await page.goto("/projets/nouveau");
  await page.getByLabel(/Titre du projet/).fill(title);
  await page.getByRole("button", { name: "Étape 7 : Public cible" }).click();
  await page.getByRole("button", { name: "Créer mon projet" }).click();

  await expect(page).toHaveURL(/\/projets\/[0-9a-f-]{36}/);
  return page.url().split("/projets/")[1].split(/[/?]/)[0];
}

import { expect, test } from "@playwright/test";

import { createProject, freshEmail, registerAndVerify } from "./helpers";

test.describe("Export", () => {
  test("l'offre gratuite se voit refuser l'export, sans ambiguïté", async ({ page }) => {
    await registerAndVerify(page, freshEmail("export"));
    const projectId = await createProject(page, "Projet non exportable");

    await page.goto(`/projets/${projectId}/budget`);
    await page.getByRole("button", { name: "Exporter en tableur" }).click();

    // 402 explicite plutôt qu'un fichier vide ou un export silencieux.
    await expect(page.getByText(/n'est pas incluse? dans l'offre/i)).toBeVisible({
      timeout: 20_000,
    });
  });
});

/**
 * Utilitaires de présentation indépendants de la langue.
 *
 * Dates, nombres et accords dépendent de la langue affichée : ils sont
 * fournis par `useI18n()` (`src/lib/i18n`), qui connaît la locale en cours.
 * Les mettre ici reviendrait à figer `fr-FR` dans des fonctions appelées
 * partout, ce qui était le cas avant l'internationalisation.
 */

export function classNames(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(" ");
}

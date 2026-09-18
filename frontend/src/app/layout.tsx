import type { Metadata } from "next";

import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "FilmFund Africa — De l'idée au financement de votre projet audiovisuel",
    template: "%s · FilmFund Africa",
  },
  description:
    "Développez votre projet audiovisuel, créez votre dossier professionnel et découvrez les financements adaptés à votre film.",
  metadataBase: new URL("https://filmfundafrica.com"),
};

/**
 * Les polices sont chargées au runtime via une feuille de style plutôt qu'avec
 * `next/font`, qui les télécharge au moment du build : cela permet de
 * construire l'image Docker dans un environnement sans accès à Google Fonts.
 * Les piles de repli système sont définies dans `tailwind.config.ts`.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap"
        />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

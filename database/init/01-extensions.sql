-- Extensions PostgreSQL utilisées par FilmFund Africa.
-- Exécuté automatiquement au premier démarrage du conteneur postgres.

-- Recherche plein texte tolérante aux fautes sur les opportunités (Phase 3).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Fonctions de normalisation de texte (accents) pour la recherche.
CREATE EXTENSION IF NOT EXISTS unaccent;

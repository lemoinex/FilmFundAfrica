#!/usr/bin/env bash
# Démarre une API jetable pour les tests de bout en bout Playwright.
#
# Base SQLite neuve à chaque lancement, fournisseur d'IA `mock`, limitation de
# débit relevée : les tests enchaînent les requêtes plus vite qu'un humain.
#
# `ENVIRONMENT=development` est délibéré : c'est le seul mode où l'API renvoie
# le jeton de confirmation d'adresse dans sa réponse. Sans lui, aucun test ne
# pourrait activer un compte sans serveur SMTP.
set -euo pipefail

PORT="${E2E_API_PORT:-8010}"
PYTHON="${E2E_PYTHON:-python3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${E2E_DB:-$ROOT/backend/.e2e.db}"

rm -f "$DB"

cd "$ROOT/backend"
export ENVIRONMENT=development
export DEBUG=false
export JWT_SECRET=e2e-secret-jamais-utilise-en-production-0123456789
export AI_PROVIDER=mock
# Les parcours de bout en bout commencent tous par une inscription, fermée en
# bêta privée. C'est la phase commerciale qu'ils rejouent — celle où tout est
# ouvert et où toutes les règles d'offre s'appliquent.
export PLATFORM_MODE=public
export DATABASE_URL="sqlite:///$DB"
export RATE_LIMIT_AUTH_PER_MINUTE=1000
export RATE_LIMIT_AI_PER_MINUTE=1000
export REDIS_URL=""
export FRONTEND_URL="http://127.0.0.1:${E2E_WEB_PORT:-3100}"
# Le navigateur des tests appelle l'API depuis une autre origine que celle de
# développement : sans cette ligne, chaque requête serait bloquée par CORS.
export CORS_ORIGINS="http://127.0.0.1:${E2E_WEB_PORT:-3100},http://localhost:${E2E_WEB_PORT:-3100}"

"$PYTHON" -m alembic upgrade head
exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --log-level warning

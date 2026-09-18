#!/usr/bin/env bash
# Suite de vérification complète : tests backend, lint, typage et build frontend.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "── Backend : tests ──────────────────────────────────"
(cd backend && python -m pytest)

echo "── Backend : lint ───────────────────────────────────"
(cd backend && ruff check .)

echo "── Frontend : typage ────────────────────────────────"
(cd frontend && npm run typecheck)

echo "── Frontend : build ─────────────────────────────────"
(cd frontend && npm run build)

echo "✓ Toutes les vérifications sont passées."

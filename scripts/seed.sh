#!/usr/bin/env bash
# Crée les données de démonstration (comptes, projets, opportunités fictives).
set -euo pipefail
cd "$(dirname "$0")/.."

if docker compose ps --status running backend >/dev/null 2>&1; then
  docker compose exec backend python -m scripts.seed "$@"
else
  cd backend && python -m scripts.seed "$@"
fi

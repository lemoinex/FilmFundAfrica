#!/usr/bin/env bash
# Démarre la pile complète en développement (Docker Compose).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "→ .env absent : copie depuis .env.example"
  cp .env.example .env
  echo "  Pensez à définir JWT_SECRET (openssl rand -hex 32) et POSTGRES_PASSWORD."
fi

docker compose up --build

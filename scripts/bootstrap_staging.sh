#!/usr/bin/env bash
# یک‌کلیکی بالا آوردن محیط Staging
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> [staging] Preparing env file..."
if [[ ! -f .env.staging ]]; then
  cp .env.staging.example .env.staging
  echo "    created .env.staging from example"
fi

echo "==> [staging] Installing Python deps (local bootstrap helpers)..."
pip install -e ".[dev]" >/dev/null

echo "==> [staging] Building dashboard (required for API static mount)..."
(cd dashboard && npm install && npm run build)

echo "==> [staging] Starting compose stack..."
docker compose -f docker-compose.staging.yml up -d --build

echo "==> [staging] Waiting for API health..."
for i in $(seq 1 40); do
  if curl -sf http://localhost:8000/api/v1/health/live >/dev/null 2>&1; then
    echo "    API is up"
    break
  fi
  if [[ "$i" -eq 40 ]]; then
    echo "ERROR: API did not become healthy in time" >&2
    docker compose -f docker-compose.staging.yml logs --tail=80 api
    exit 1
  fi
  sleep 3
done

echo "==> [staging] Seeding users / synthetic data (best-effort)..."
python scripts/seed_users.py || true
python data/generate_synthetic.py --mode training -n 200 || true

echo ""
echo "Staging ready"
echo "  Dashboard / API: http://localhost:8000"
echo "  OpenAPI docs:    set DEBUG=true temporarily or use /api/v1/health"
echo "  MinIO console:   http://localhost:9011"
echo "  Postgres:        localhost:5433"
echo ""
echo "Smoke checklist:"
echo "  1) login  2) create patient  3) upload sample  4) run pipeline  5) open report + audit"

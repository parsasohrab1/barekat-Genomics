#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting infrastructure..."
docker compose up -d postgres redis minio

echo "==> Waiting for services..."
sleep 5

echo "==> Installing dependencies..."
pip install -e ".[dev]"

echo "==> Running migrations..."
alembic upgrade head

echo "==> Generating synthetic data..."
python data/generate_synthetic.py

echo "==> Building dashboard..."
cd dashboard && npm install && npm run build && cd ..

echo "==> Running tests..."
pytest tests/ -v

echo "==> Starting API..."
docker compose up -d api worker

echo ""
echo "Infrastructure ready!"
echo "  Dashboard: http://localhost:8000"
echo "  API:       http://localhost:8000/docs"
echo "  Dev UI:    http://localhost:5173"
echo "  MinIO:     http://localhost:9001"
echo "  DB:        postgresql://barekat:barekat@localhost:5432/barekat_genomics"

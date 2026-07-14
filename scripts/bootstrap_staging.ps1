# یک‌کلیکی Staging برای Windows (PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> [staging] Preparing env file..."
if (-not (Test-Path ".env.staging")) {
  Copy-Item ".env.staging.example" ".env.staging"
  Write-Host "    created .env.staging from example"
}

Write-Host "==> [staging] Installing Python deps..."
pip install -e ".[dev]" | Out-Null

Write-Host "==> [staging] Building dashboard..."
Push-Location dashboard
npm install
npm run build
Pop-Location

Write-Host "==> [staging] Starting compose stack..."
docker compose -f docker-compose.staging.yml up -d --build

Write-Host "==> [staging] Waiting for API health..."
$ok = $false
for ($i = 1; $i -le 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/live" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $ok = $true; break }
  } catch { }
  Start-Sleep -Seconds 3
}
if (-not $ok) {
  Write-Error "API did not become healthy in time"
  docker compose -f docker-compose.staging.yml logs --tail=80 api
  exit 1
}

Write-Host "==> [staging] Seeding (best-effort)..."
try { python scripts/seed_users.py } catch { }
try { python data/generate_synthetic.py --mode training -n 200 } catch { }

Write-Host ""
Write-Host "Staging ready"
Write-Host "  Dashboard / API: http://localhost:8000"
Write-Host "  MinIO console:   http://localhost:9011"
Write-Host "  Postgres:        localhost:5433"

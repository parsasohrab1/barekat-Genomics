# barekat-Genomics

Genomic and pharmacogenomic data analysis platform for identifying biomarkers and predicting drug response.

## Quick start

```bash
cp .env.example .env
docker compose up -d
pip install -e ".[dev]"
alembic upgrade head
python data/generate_synthetic.py          # all outputs
python data/generate_synthetic.py --mode benchmark
python data/generate_synthetic.py --mode training -n 2000

# Dashboard
cd dashboard && npm install && npm run build && cd ..
uvicorn barekat_genomics.api.main:app --reload
```

### Synthetic data

| Path | Purpose |
|------|--------|
| `data/synthetic_genomics.csv` | Full dataset with Gaussian Copula LD |
| `data/benchmark/pipeline_*.csv/json` | Pipeline test ground truth |
| `data/training/anonymized_training.csv` | ML model training (no PHI) |

| Service | Address |
|--------|------|
| **Dashboard** | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Dashboard (development) | http://localhost:5173 |

Infrastructure documentation: [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
Operator guide: [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md)

### One-click staging

```bash
cp .env.staging.example .env.staging
bash scripts/bootstrap_staging.sh
# Windows: powershell -File scripts/bootstrap_staging.ps1
```

## Dashboard

A professional web dashboard with a **header** and **sidebar** — connected to the real API:

- Register patients and upload samples (FASTQ/BAM) from the UI
- Pipeline with automatic polling (every 4 seconds)
- Report with variant details and drug recommendation
- EHR export to JSON

```bash
cd dashboard
npm install
npm run dev      # development — port 5173 (proxy to the API)
npm run build    # build for production
```

## Bioinformatics pipeline

```
FASTQ → FastQC/MultiQC → BWA-MEM2 → GATK HaplotypeCaller → SnpEff → ML interpretation
```

| Mode | `PIPELINE_MODE` | Description |
|------|-----------------|--------|
| Simulation | `simulated` | Default — development and testing |
| Production | `production` | Separate worker with `docker/bio/Dockerfile` |

Genome reference: [data/reference/README.md](data/reference/README.md)

```bash
docker compose build worker
docker compose up worker
```

---

## Goal: to provide a platform for analyzing genomic and pharmacogenomic data to identify biomarkers and predict drug response.

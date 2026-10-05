# Infrastructure

## Architecture

```
┌──────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  React Dashboard │────▶│  FastAPI     │────▶│  PostgreSQL     │
│  (Header+Sidebar)│     │  REST API    │     │  (Variants)     │
└──────────────────┘     └──────┬───────┘     └─────────────────┘
                                  │
                                  ▼
                         ┌──────────────┐     ┌─────────────────┐
                         │   Celery     │────▶│  MinIO (S3)     │
                         │   Worker     │     │  (FASTQ/BAM)    │
                         └──────────────┘     └─────────────────┘
                                  │
                                  ▼
                         Pipeline: QC → Variant → Interpret
```

## Staging

```bash
docker compose -f docker-compose.staging.yml up -d --build
# or: bash scripts/bootstrap_staging.sh
```

| Service | Port |
|--------|------|
| API/Dashboard | 8000 |
| Postgres | 5433 |
| Redis | 6380 |
| MinIO | 9010 / 9011 |

Operator guide: [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md)

## Dashboard

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Overall statistics, charts, recent activity |
| Patients | `/patients` | Patient list and search |
| Samples | `/samples` | FASTQ/BAM upload and status |
| Pipeline | `/pipeline` | Processing jobs and progress |
| Reports | `/reports` | Genomic reports and EHR |
| Report | `/reports/:id` | Variant details and drug recommendation |
| Variants | `/variants` | Variants with ML prioritization |
| Settings | `/settings` | HIPAA, ML model, EHR |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/dashboard/stats` | Dashboard statistics |
| GET | `/api/v1/samples/` | List samples |
| GET | `/api/v1/pipeline/jobs` | List pipeline jobs |
| GET | `/api/v1/variants/` | List variants with annotations |
| GET | `/api/v1/reports/` | List all reports |
| POST | `/api/v1/pipeline/run?sync=true` | Run pipeline (sync mode) |
| POST | `/api/v1/patients/` | Create patient |
| POST | `/api/v1/samples/upload` | Upload FASTQ/BAM |
| POST | `/api/v1/pipeline/run` | Start processing |
| GET | `/api/v1/reports/{id}` | Get genomic report |
| GET | `/api/v1/ehr/export/{patient_id}` | EHR integration |

## Components

- **dashboard/**: React + Vite + Tailwind dashboard (RTL, Persian)
- **docker/bio/**: Bioinformatics worker image (FastQC, BWA-MEM2, GATK, SnpEff)
- **pipeline/**: QC → Alignment → Variant Calling → Annotation → ML Interpretation
- **core/**: Config, database, HIPAA security, audit logging, S3 storage
- **models/**: SQLAlchemy ORM (patients, samples, variants, reports)
- **api/**: FastAPI REST endpoints + static dashboard serving
- **tasks/**: Celery async processing (bio-worker container)
- **ml/**: RandomForest variant classifier

## Bioinformatics Pipeline

```
FASTQ → FastQC/MultiQC → BWA-MEM2 → MarkDuplicates → GATK HaplotypeCaller → SnpEff → Interpretation
BAM   → samtools QC → MarkDuplicates → GATK HaplotypeCaller → SnpEff → Interpretation
```

| Mode | Env | Description |
|------|-----|-------------|
| `simulated` | `PIPELINE_MODE=simulated` | Default — no external tools |
| `production` | `PIPELINE_MODE=production` | Real tools in `docker/bio` worker |

### Reference / MinIO / Benchmark

```bash
python scripts/setup_reference.py validate
python scripts/setup_reference.py upload-minio
python scripts/validate_pipeline_benchmark.py --write docs/PIPELINE_VALIDATION.md
```

| Method | Endpoint |
|--------|----------|
| GET | `/api/v1/pipeline/reference/status` |
| GET | `/api/v1/pipeline/benchmark/metrics` |
| GET | `/api/v1/pipeline/jobs/{id}/qc` |
| GET | `/api/v1/samples/{id}/qc` |

Reference setup: [data/reference/README.md](../data/reference/README.md)

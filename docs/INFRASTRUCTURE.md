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

## Quick Start

```bash
cp .env.example .env
docker compose up -d
pip install -e ".[dev]"
alembic upgrade head
python data/generate_synthetic.py

cd dashboard && npm install && npm run build && cd ..
uvicorn barekat_genomics.api.main:app --reload
```

- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Dev Dashboard: http://localhost:5173 (with `npm run dev`)

## Dashboard

| Page | Route | Description |
|------|-------|-------------|
| داشبورد | `/` | آمار کلی، نمودارها، فعالیت‌های اخیر |
| بیماران | `/patients` | لیست و جستجوی بیماران |
| نمونه‌ها | `/samples` | آپلود و وضعیت FASTQ/BAM |
| پایپ‌لاین | `/pipeline` | وظایف پردازش و پیشرفت |
| گزارش‌ها | `/reports` | گزارش‌های ژنومی و EHR |
| واریانت‌ها | `/variants` | واریانت‌ها با اولویت‌بندی ML |
| تنظیمات | `/settings` | HIPAA، مدل ML، EHR |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/patients/` | Create patient |
| POST | `/api/v1/samples/upload` | Upload FASTQ/BAM |
| POST | `/api/v1/pipeline/run` | Start processing |
| GET | `/api/v1/reports/{id}` | Get genomic report |
| GET | `/api/v1/ehr/export/{patient_id}` | EHR integration |

## Components

- **dashboard/**: React + Vite + Tailwind dashboard (RTL, Persian)
- **core/**: Config, database, HIPAA security, audit logging, S3 storage
- **models/**: SQLAlchemy ORM (patients, samples, variants, reports)
- **pipeline/**: QC, variant calling, ML interpretation
- **api/**: FastAPI REST endpoints + static dashboard serving
- **tasks/**: Celery async processing
- **ml/**: RandomForest variant classifier

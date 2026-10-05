# Lab Operator Guide — barekat Genomics

This guide is for the lab operator and system administrator so they can move a sample from registration to report without development knowledge.

## 1) Prerequisites

- Docker Desktop / Docker Engine
- Python 3.10+ and Node 20+ (only for local bootstrap/Staging)
- At least 8 GB RAM for compose

## 2) One-click Staging deployment

```bash
# Linux / macOS
cp .env.staging.example .env.staging
bash scripts/bootstrap_staging.sh
```

```powershell
# Windows
Copy-Item .env.staging.example .env.staging
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_staging.ps1
```

Services:

| Service | Address |
|--------|------|
| Dashboard and API | http://localhost:8000 |
| Health | http://localhost:8000/api/v1/health/live |
| MinIO | http://localhost:9011 |
| Postgres Staging | localhost:5433 |

Stop:

```bash
docker compose -f docker-compose.staging.yml down
```

## 3) Operator workflow (10 minutes)

1. Log in to the dashboard (seeded user or admin).
2. **Patients** → register a new patient with a unique external ID.
3. **Samples** → upload FASTQ or BAM and select the patient.
4. **Pipeline** → run processing (in Staging usually `simulated` mode).
5. Wait until the Job status reaches `completed`.
6. **Reports** → view variant details and drug recommendation (CPIC).
7. Download the PDF if needed.
8. **Audit** → review the PHI access log.

## 4) Genomic / pharmacogenomic report

A unified JSON and PDF format with `schema_version: "1.0"` including:

- `executive_summary`
- `high_priority_variants`
- `drug_recommendations` (with CPIC level)
- `drug_interactions`
- `digital_signature` (after approval)
- `metadata` (reference genome and patient ID)

JSON schema: `schemas/clinical_report.v1.json`.

## 5) HIPAA and Audit

- Recorded events: patient creation/view, sample upload, pipeline run, report view/download/approval, variant review, EHR export, AI questions.
- Enable with `AUDIT_LOG_ENABLED=true`.
- Suggested retention: `PHI_RETENTION_DAYS=2555` (~7 years).
- The **Settings** page shows the real server values (HIPAA, pipeline, EHR, ML).

## 6) Key API references

| Method | Endpoint | Description |
|--------|----------|--------|
| GET | `/api/v1/health/live` | Service liveness |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/patients/` | Register patient |
| POST | `/api/v1/samples/upload` | Upload sample |
| POST | `/api/v1/pipeline/run?sync=true` | Run pipeline |
| GET | `/api/v1/reports/{id}` | JSON report |
| GET | `/api/v1/reports/{id}/pdf` | PDF report |
| GET | `/api/v1/audit/logs` | Audit log |
| GET | `/api/v1/settings/` | Platform settings (admin) |

In development mode (`DEBUG=true`) interactive documentation is available at `/docs`.

## 7) Common troubleshooting

| Problem | Action |
|------|--------|
| Job stays in queued | Check worker and Redis status |
| Upload fails | Check MinIO and the `data/uploads` path |
| PDF is not generated | A Persian font (Vazirmatn/Noto/Tahoma) must be installed |
| Settings are empty | The user role must be `admin` |
| Report cannot be approved | First complete the genetic review queue |

## 8) Demo checklist

- [ ] Health = alive
- [ ] Patient + sample created
- [ ] Simulated pipeline succeeded
- [ ] JSON report has `schema_version=1.0`
- [ ] PDF downloaded
- [ ] Events are visible in Audit

More infrastructure documentation: [INFRASTRUCTURE.md](INFRASTRUCTURE.md)

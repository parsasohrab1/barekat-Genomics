# Partner Public API (B2B)

Base URL: `/api/v1/partner`

Authentication: header `X-API-Key: bk_live_...`

Keys are created by org admins via `POST /api/v1/integrations/api-keys` (returned once).

## Endpoints

| Method | Path | Scope | Description |
|--------|------|-------|-------------|
| GET | `/partner/health` | any | اتصال و قابلیت‌ها |
| POST | `/partner/patients` | `samples:write` | ایجاد بیمار |
| POST | `/partner/pipeline/run` | `pipeline:run` | اجرای workflow با کش |

### Sample pipeline body

```json
{
  "file_path": "/data/samples/demo.vcf",
  "file_type": "VCF",
  "assay_type": "panel",
  "genome_build": "GRCh38",
  "module_id": "pgx",
  "use_cache": true
}
```

`assay_type`: `wgs` | `wes` | `panel`  
`file_type`: `FASTQ` | `BAM` | `VCF` | `CRAM`

Rate limit: per-key (default 60 req/min). Response `429` on exceed.

## Related platform APIs

- Cohorts: `/api/v1/cohorts`
- Compute/cache summary: `/api/v1/integrations/compute/summary`
- Knowledge assets: `/api/v1/knowledge-assets`

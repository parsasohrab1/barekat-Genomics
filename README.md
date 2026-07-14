# barekat-Genomics

پلتفرم تحلیل داده‌های ژنومی و فارماکوژنومیک برای شناسایی نشانگرهای زیستی و پیش‌بینی پاسخ به دارو.

## شروع سریع

```bash
cp .env.example .env
docker compose up -d
pip install -e ".[dev]"
alembic upgrade head
python data/generate_synthetic.py          # همه خروجی‌ها
python data/generate_synthetic.py --mode benchmark
python data/generate_synthetic.py --mode training -n 2000

# داشبورد
cd dashboard && npm install && npm run build && cd ..
uvicorn barekat_genomics.api.main:app --reload
```

### داده سنتتیک

| مسیر | کاربرد |
|------|--------|
| `data/synthetic_genomics.csv` | دیتاست کامل با Gaussian Copula LD |
| `data/benchmark/pipeline_*.csv/json` | ground truth تست پایپ‌لاین |
| `data/training/anonymized_training.csv` | آموزش مدل ML (بدون PHI) |

| سرویس | آدرس |
|--------|------|
| **داشبورد** | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| داشبورد (توسعه) | http://localhost:5173 |

مستندات زیرساخت: [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
راهنمای اپراتور: [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md)

### Staging یک‌کلیکی

```bash
cp .env.staging.example .env.staging
bash scripts/bootstrap_staging.sh
# Windows: powershell -File scripts/bootstrap_staging.ps1
```

## داشبورد

داشبورد وب حرفه‌ای با **هدر** و **سایدبار** — متصل به API واقعی:

- ثبت بیمار و آپلود نمونه (FASTQ/BAM) از UI
- پایپ‌لاین با polling خودکار (هر ۴ ثانیه)
- گزارش با جزئیات واریانت و توصیه دارویی
- خروجی EHR به JSON

```bash
cd dashboard
npm install
npm run dev      # توسعه — پورت 5173 (proxy به API)
npm run build    # ساخت برای production
```

## پایپ‌لاین Bioinformatics

```
FASTQ → FastQC/MultiQC → BWA-MEM2 → GATK HaplotypeCaller → SnpEff → تفسیر ML
```

| حالت | `PIPELINE_MODE` | توضیح |
|------|-----------------|--------|
| شبیه‌سازی | `simulated` | پیش‌فرض — توسعه و تست |
| تولید | `production` | worker جدا با `docker/bio/Dockerfile` |

مرجع ژنوم: [data/reference/README.md](data/reference/README.md)

```bash
docker compose build worker
docker compose up worker
```

---

## هدف: ارائه یک پلتفرم برای تحلیل داده‌های ژنومی و فارماکوژنومیک به منظور شناسایی نشانگرهای زیستی و پیش‌بینی پاسخ به دارو.

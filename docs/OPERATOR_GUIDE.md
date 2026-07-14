# راهنمای اپراتور آزمایشگاه — barekat Genomics

این راهنما برای اپراتور آزمایشگاه و مدیر سیستم است تا بدون دانش توسعه بتواند نمونه را از ثبت تا گزارش جلو ببرد.

## ۱) پیش‌نیاز

- Docker Desktop / Docker Engine
- Python 3.10+ و Node 20+ (فقط برای bootstrap محلی/Staging)
- حداقل ۸ گیگ RAM برای compose

## ۲) استقرار Staging یک‌کلیکی

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

سرویس‌ها:

| سرویس | آدرس |
|--------|------|
| داشبورد و API | http://localhost:8000 |
| Health | http://localhost:8000/api/v1/health/live |
| MinIO | http://localhost:9011 |
| Postgres Staging | localhost:5433 |

توقف:

```bash
docker compose -f docker-compose.staging.yml down
```

## ۳) گردش کار اپراتور (۱۰ دقیقه)

1. ورود به داشبورد (کاربر seed‌شده یا ادمین).
2. **بیماران** → ثبت بیمار جدید با شناسه خارجی یکتا.
3. **نمونه‌ها** → آپلود FASTQ یا BAM و انتخاب بیمار.
4. **پایپ‌لاین** → اجرای پردازش (در Staging معمولاً حالت `simulated`).
5. انتظار تا وضعیت Job به `completed` برسد.
6. **گزارش‌ها** → مشاهده جزئیات واریانت و توصیه دارویی (CPIC).
7. در صورت نیاز دانلود PDF.
8. **ممیزی** → بررسی لاگ دسترسی به PHI.

## ۴) گزارش ژنومی / فارماکوژنومیک

قالب یکپارچه JSON و PDF با `schema_version: "1.0"` شامل:

- `executive_summary`
- `high_priority_variants`
- `drug_recommendations` (با سطح CPIC)
- `drug_interactions`
- `digital_signature` (پس از تأیید)
- `metadata` (ژنوم مرجع و شناسه بیمار)

اسکمای JSON: `schemas/clinical_report.v1.json`.

## ۵) HIPAA و Audit

- رویدادهای ثبت‌شده: ایجاد/مشاهده بیمار، آپلود نمونه، اجرای پایپ‌لاین، مشاهده/دانلود/تأیید گزارش، بررسی واریانت، خروجی EHR، سوالات AI.
- فعال‌سازی با `AUDIT_LOG_ENABLED=true`.
- مدت نگهداری پیشنهادی: `PHI_RETENTION_DAYS=2555` (~۷ سال).
- صفحه **تنظیمات** مقادیر واقعی سرور (HIPAA، پایپ‌لاین، EHR، ML) را نشان می‌دهد.

## ۶) مراجع API کلیدی

| Method | Endpoint | توضیح |
|--------|----------|--------|
| GET | `/api/v1/health/live` | زنده بودن سرویس |
| POST | `/api/v1/auth/login` | ورود |
| POST | `/api/v1/patients/` | ثبت بیمار |
| POST | `/api/v1/samples/upload` | آپلود نمونه |
| POST | `/api/v1/pipeline/run?sync=true` | اجرای پایپ‌لاین |
| GET | `/api/v1/reports/{id}` | گزارش JSON |
| GET | `/api/v1/reports/{id}/pdf` | گزارش PDF |
| GET | `/api/v1/audit/logs` | لاگ ممیزی |
| GET | `/api/v1/settings/` | تنظیمات پلتفرم (admin) |

در حالت توسعه (`DEBUG=true`) مستندات تعاملی در `/docs` در دسترس است.

## ۷) عیب‌یابی رایج

| مشکل | اقدام |
|------|--------|
| Job در queued می‌ماند | وضعیت worker و Redis را چک کنید |
| آپلود شکست می‌خورد | MinIO و مسیر `data/uploads` را بررسی کنید |
| PDF ساخته نمی‌شود | فونت فارسی (Vazirmatn/Noto/Tahoma) نصب باشد |
| تنظیمات خالی است | نقش کاربر باید `admin` باشد |
| گزارش تأیید نمی‌شود | ابتدا صف بررسی ژنتیکی را تکمیل کنید |

## ۸) چک‌لیست دمو

- [ ] Health = alive
- [ ] بیمار + نمونه ساخته شد
- [ ] پایپ‌لاین simulated موفق شد
- [ ] گزارش JSON دارای `schema_version=1.0` است
- [ ] PDF دانلود شد
- [ ] رویدادها در Audit دیده می‌شوند

مستندات زیرساخت بیشتر: [INFRASTRUCTURE.md](INFRASTRUCTURE.md)

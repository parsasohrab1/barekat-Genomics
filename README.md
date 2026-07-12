# barekat-Genomics

پلتفرم تحلیل داده‌های ژنومی و فارماکوژنومیک برای شناسایی نشانگرهای زیستی و پیش‌بینی پاسخ به دارو.

## شروع سریع

```bash
cp .env.example .env
docker compose up -d
pip install -e ".[dev]"
alembic upgrade head
python data/generate_synthetic.py

# داشبورد
cd dashboard && npm install && npm run build && cd ..
uvicorn barekat_genomics.api.main:app --reload
```

| سرویس | آدرس |
|--------|------|
| **داشبورد** | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| داشبورد (توسعه) | http://localhost:5173 |

مستندات زیرساخت: [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)

## داشبورد

داشبورد وب حرفه‌ای با **هدر** و **سایدبار** شامل:

- نمای کلی (آمار، نمودارها، فعالیت‌های اخیر)
- مدیریت بیماران، نمونه‌ها، پایپ‌لاین
- گزارش‌های ژنومی و واریانت‌های فارماکوژنومیک
- تنظیمات امنیت HIPAA و اتصال EHR

```bash
cd dashboard
npm install
npm run dev      # توسعه — پورت 5173
npm run build    # ساخت برای production
```

---

## هدف: ارائه یک پلتفرم برای تحلیل داده‌های ژنومی و فارماکوژنومیک به منظور شناسایی نشانگرهای زیستی و پیش‌بینی پاسخ به دارو.
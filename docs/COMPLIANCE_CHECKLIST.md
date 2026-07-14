"""Checklist انطباق رگولاتوری (GDPR-like / وزارت بهداشت / HIPAA).

این سند وضعیت نسبی آمادگی پلتفرم barekat Genomics را توصیف می‌کند.
وضعیت زنده از API نیز در دسترس است:

  GET /api/v1/compliance/checklist

## نقش‌های محصولی RBAC

| نقش محصول | نقش داخلی (سازگار) | دسترسی کلیدی |
|-----------|---------------------|---------------|
| Admin | admin | همه مجوزها، کاربران، سازمان، صورتحساب |
| Analyst | analyst / geneticist | تفسیر واریانت، تأیید گزارش، EHR |
| Physician | physician / clinician | بیماران خود، گزارش‌های تأییدشده |
| Lab Tech | lab_tech | نمونه و پایپ‌لاین |

## کنترل‌های پیاده‌سازی‌شده

1. احراز هویت JWT و ماتریس مجوزها
2. رمزنگاری فیلد نام بیمار (PHI)
3. لاگ ممیزی دسترسی و خروجی EHR
4. ایزولاسیون چندسازمانی (`organization_id`)
5. Export/Import استاندارد FHIR R4 و HL7 v2
6. حق دسترسی سوژه (`/compliance/subjects/{id}/export`)
7. ناشناس‌سازی نسبی PHI (`/erase`)

## موارد جزئی / در برنامه

- رضایت آگاهانه ساختاریافته (Consent entity)
- Job پاک‌سازی بر اساس `phi_retention_days`
- رویه نقض داده و اطلاع‌رسانی
- DPIA رسمی برای استقرار بیمارستانی

## وزارت بهداشت / تبادلات ملی

- کانکتورهای `sepas` و `tajhiz` برای push خروجی
- شناسه‌های Organization در FHIR قابل پیکربندی‌اند
- استقرار On-prem از طریق پلن `enterprise_onprem`

## مدل درآمد

| پلن | حالت | محدودیت نمونه/ماه |
|-----|------|---------------------|
| starter | SaaS | 50 |
| professional | SaaS | 500 |
| enterprise_onprem | On-prem | بسیار بالا |

API: `/api/v1/billing/plans`, `/subscribe`, `/usage`
"""

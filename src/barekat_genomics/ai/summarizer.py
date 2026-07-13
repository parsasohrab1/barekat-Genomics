"""خلاصه‌سازی گزارش به زبان ساده فارسی — پشتیبان تصمیم."""

from __future__ import annotations

from barekat_genomics.ai.disclaimer import (
    DECISION_SUPPORT_BANNER,
    FULL_DISCLAIMER_FA,
    SHORT_DISCLAIMER_FA,
)

SIGNIFICANCE_PLAIN: dict[str, str] = {
    "pathogenic": "این تغییر ژنتیکی احتمالاً مضر است و ممکن است عملکرد ژن را تحت تأثیر قرار دهد",
    "likely_pathogenic": "این تغییر احتمال زیادی دارد که مضر باشد",
    "drug_response": "این تغییر مستقیماً با پاسخ بدن به دارو مرتبط است",
    "uncertain_significance": "اهمیت بالینی این تغییر هنوز قطعی نیست",
    "likely_benign": "این تغییر احتمالاً بی‌ضرر است",
    "benign": "این تغییر معمولاً بی‌ضرر در نظر گرفته می‌شود",
}

CPIC_LEVEL_PLAIN: dict[str, str] = {
    "A": "شواهد قوی — توصیه دارویی با اطمینان بالا",
    "B": "شواهد متوسط — توصیه دارویی با احتیاط",
    "C": "شواهد محدود — تصمیم با پزشک",
    "D": "بدون توصیه مشخص — ادامه پروتکل معمول",
}


def summarize_report_plain(clinical_content: dict, *, patient_label: str | None = None) -> dict:
    """تبدیل محتوای بالینی به پاراگراف‌های ساده فارسی."""
    paragraphs: list[str] = [DECISION_SUPPORT_BANNER]

    patient_ref = f"بیمار {patient_label}" if patient_label else "بیمار"
    paragraphs.append(f"خلاصه ساده برای {patient_ref}:")

    hp = clinical_content.get("high_priority_variants") or []
    if hp:
        paragraphs.append(
            f"در آزمایش ژنی، {len(hp)} مورد مهم پیدا شد که ممکن است روی داروها یا درمان اثر بگذارد:"
        )
        for v in hp[:6]:
            gene = v.get("gene") or "ژن نامشخص"
            rs = v.get("rs_id") or f"{v.get('chromosome')}:{v.get('position')}"
            sig_plain = SIGNIFICANCE_PLAIN.get(
                v.get("clinical_significance", ""),
                "نیاز به بررسی بیشتر دارد",
            )
            paragraphs.append(f"• {gene} ({rs}): {sig_plain}.")
    else:
        paragraphs.append(
            "در این آزمایش، واریانت با اهمیت بالای بالینی شناسایی نشد. "
            "ادامه درمان معمولاً طبق پروتکل استاندارد انجام می‌شود."
        )

    drugs = clinical_content.get("drug_recommendations") or []
    if drugs:
        paragraphs.append("توصیه‌های دارویی (بر اساس راهنمای CPIC):")
        for d in drugs[:8]:
            drug_name = d.get("drug_fa") or d.get("drug", "")
            level = d.get("cpic_level", "C")
            level_plain = CPIC_LEVEL_PLAIN.get(level, "")
            action = d.get("action_fa") or d.get("recommendation") or "نیاز به بررسی پزشک"
            gene = d.get("gene") or ""
            gene_part = f" (ژن {gene})" if gene else ""
            paragraphs.append(f"• {drug_name}{gene_part}: {action}. {level_plain}")

    interactions = clinical_content.get("drug_interactions") or []
    if interactions:
        paragraphs.append(f"توجه: {len(interactions)} تداخل احتمالی بین داروها شناسایی شد — بازنگری نسخه توصیه می‌شود.")

    module = clinical_content.get("module_analysis")
    if module and module.get("summary_fa"):
        paragraphs.append(f"تحلیل ماژول: {module['summary_fa']}")

    paragraphs.append(SHORT_DISCLAIMER_FA)

    return {
        "plain_summary": paragraphs,
        "plain_summary_text": "\n\n".join(paragraphs),
        "disclaimer": FULL_DISCLAIMER_FA,
        "decision_support_only": True,
        "source": "rule_based",
    }

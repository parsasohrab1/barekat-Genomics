"""ساخت محتوای گزارش بالینی برای پزشک."""

from __future__ import annotations

from barekat_genomics.core.review import ML_REVIEW_THRESHOLD, VARIANT_REVIEW_REJECTED
from barekat_genomics.pipeline.cpic import (
    CPIC_LEVEL_LABELS,
    detect_drug_interactions,
    get_cpic_info,
)
from barekat_genomics.pipeline.interpretation import VariantInterpretation
from barekat_genomics.pipeline.variant_calling import CalledVariant

HIGH_PRIORITY_THRESHOLD = ML_REVIEW_THRESHOLD


def build_clinical_report(
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
    drug_recommendations: dict,
    *,
    patient_external_id: str | None = None,
    genome_build: str = "GRCh38",
    review_status_by_key: dict[str, str] | None = None,
) -> dict:
    high_priority = _build_high_priority_variants(
        interpretations,
        review_status_by_key=review_status_by_key,
    )
    enriched_drugs = _build_drug_recommendations(drug_recommendations)
    interactions = detect_drug_interactions(list(drug_recommendations.keys()))
    executive_summary = _build_executive_summary(
        interpretations,
        high_priority,
        enriched_drugs,
        interactions,
        patient_external_id,
        genome_build,
    )

    return {
        "executive_summary": executive_summary,
        "high_priority_variants": high_priority,
        "drug_recommendations": enriched_drugs,
        "drug_interactions": interactions,
        "digital_signature": None,
    }


def _build_high_priority_variants(
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
    *,
    review_status_by_key: dict[str, str] | None = None,
) -> list[dict]:
    rows = []
    for variant, interp in interpretations:
        if interp.ml_score <= HIGH_PRIORITY_THRESHOLD:
            continue
        key = variant.rs_id or f"{variant.chromosome}:{variant.position}"
        if review_status_by_key and review_status_by_key.get(key) == VARIANT_REVIEW_REJECTED:
            continue
        rows.append(
            {
                "gene": interp.gene,
                "rs_id": variant.rs_id,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "ref_allele": variant.ref_allele,
                "alt_allele": variant.alt_allele,
                "clinical_significance": interp.clinical_significance,
                "priority_score": round(interp.priority_score, 3),
                "interpretation": interp.interpretation,
                "pharmacogenomic_effect": interp.pharmacogenomic_effect,
            }
        )
    return rows


def _build_drug_recommendations(drug_recommendations: dict) -> list[dict]:
    enriched = []
    for drug, rec in drug_recommendations.items():
        cpic = get_cpic_info(drug, rec.get("gene"))
        enriched.append(
            {
                "drug": drug,
                "drug_fa": cpic.get("drug_fa", drug),
                "gene": rec.get("gene") or cpic.get("gene"),
                "significance": rec.get("significance"),
                "recommendation": rec.get("recommendation"),
                "confidence": rec.get("confidence"),
                "cpic_level": cpic.get("cpic_level", "C"),
                "cpic_level_label": CPIC_LEVEL_LABELS.get(cpic.get("cpic_level", "C"), ""),
                "cpic_guideline": cpic.get("guideline"),
                "action_fa": cpic.get("action_fa"),
            }
        )
    enriched.sort(key=lambda x: x.get("cpic_level", "Z"))
    return enriched


def _build_executive_summary(
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
    high_priority: list[dict],
    drugs: list[dict],
    interactions: list[dict],
    patient_external_id: str | None,
    genome_build: str,
) -> list[str]:
    total = len(interpretations)
    hp_count = len(high_priority)
    drug_count = len(drugs)
    level_a = sum(1 for d in drugs if d.get("cpic_level") == "A")

    patient_ref = f"بیمار {patient_external_id}" if patient_external_id else "بیمار"
    sentences = [
        (
            f"{patient_ref}: بر اساس تحلیل نمونه ژنومی ({genome_build})، "
            f"{total} واریانت فارماکوژنومی غربالگری و {hp_count} مورد با اهمیت بالینی بالا شناسایی شد."
        ),
    ]

    if hp_count:
        genes = ", ".join(
            dict.fromkeys(v["gene"] for v in high_priority if v.get("gene"))
        )
        if genes:
            sentences.append(
                f"واریانت‌های با اولویت بالا در ژن‌های {genes} یافت شدند که بر متابولیسم و پاسخ دارویی تأثیر مستقیم دارند."
            )

    if drug_count:
        sentences.append(
            f"بر اساس راهنمای CPIC، {drug_count} توصیه دارویی تولید شد "
            f"({level_a} مورد با سطح شواهد A — توصیه قطعی)."
        )
    else:
        sentences.append(
            "در این نمونه واریانت فارماکوژنومی با اهمیت بالینی قابل اقدام یافت نشد؛ "
            "ادامه درمان بر اساس پروتکل استاندارد توصیه می‌شود."
        )

    if interactions:
        sentences.append(
            f"هشدار: {len(interactions)} تداخل دارویی بالقوه بین داروهای توصیه‌شده شناسایی شد "
            "که نیازمند بازنگری نسخه و پایش دقیق‌تر است."
        )
    else:
        sentences.append(
            "تداخل دارویی مهمی بین داروهای توصیه‌شده در این گزارش شناسایی نشد؛ "
            "با این حال، پایش بالینی توصیه می‌شود."
        )

    sentences.append(
        "این گزارش صرفاً جنبه مشاوره‌ای دارد و جایگزین قضاوت بالینی پزشک معالج نیست؛ "
        "تصمیم نهایی درمانی با پزشک است."
    )

    return sentences[:5]


def executive_summary_text(clinical_content: dict) -> str:
    parts = clinical_content.get("executive_summary") or []
    return " ".join(parts)


def enrich_legacy_drug_recommendations(drug_recommendations: dict | None) -> list[dict]:
    if not drug_recommendations:
        return []
    return _build_drug_recommendations(drug_recommendations)


def rebuild_clinical_content_from_db(
    variants_with_annotations: list[dict],
    drug_recommendations: dict | None,
    *,
    patient_external_id: str | None = None,
) -> dict:
    """بازسازی محتوای بالینی برای گزارش‌های قدیمی از داده‌های DB."""
    interpretations: list[tuple[CalledVariant, VariantInterpretation]] = []
    for row in variants_with_annotations:
        variant = CalledVariant(
            chromosome=row["chromosome"],
            position=row["position"],
            ref_allele=row["ref_allele"],
            alt_allele=row["alt_allele"],
            variant_type=row.get("variant_type", "SNP"),
            quality_score=row.get("quality_score") or 0.0,
            depth=row.get("depth") or 30,
            rs_id=row.get("rs_id"),
            gene=row.get("gene"),
            consequence=row.get("consequence"),
        )
        ann = row.get("annotation") or {}
        interp = VariantInterpretation(
            gene=ann.get("gene"),
            consequence=ann.get("consequence"),
            clinical_significance=ann.get("clinical_significance", "uncertain_significance"),
            pharmacogenomic_effect=ann.get("pharmacogenomic_effect"),
            priority_score=ann.get("priority_score") or 0.0,
            ml_confidence=ann.get("ml_confidence") or 0.0,
            ml_score=ann.get("ml_score") or ann.get("priority_score") or 0.0,
            interpretation=ann.get("interpretation") or "",
        )
        interpretations.append((variant, interp))

    drugs = drug_recommendations or {}
    if not drugs:
        from barekat_genomics.pipeline.interpretation import generate_drug_recommendations

        drugs = generate_drug_recommendations(interpretations)

    review_map: dict[str, str] = {}
    for row in variants_with_annotations:
        ann = row.get("annotation") or {}
        if ann.get("review_status"):
            key = row.get("rs_id") or f"{row['chromosome']}:{row['position']}"
            review_map[key] = ann["review_status"]

    return build_clinical_report(
        interpretations,
        drugs,
        patient_external_id=patient_external_id,
        review_status_by_key=review_map or None,
    )

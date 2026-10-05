"""Plain-language report summarization — decision support."""

from __future__ import annotations

from barekat_genomics.ai.disclaimer import (
    DECISION_SUPPORT_BANNER,
    FULL_DISCLAIMER_FA,
    SHORT_DISCLAIMER_FA,
)

SIGNIFICANCE_PLAIN: dict[str, str] = {
    "pathogenic": "This genetic change is likely harmful and may affect gene function",
    "likely_pathogenic": "This change is highly likely to be harmful",
    "drug_response": "This change is directly related to the body's response to a drug",
    "uncertain_significance": "The clinical significance of this change is not yet definitive",
    "likely_benign": "This change is probably harmless",
    "benign": "This change is generally considered harmless",
}

CPIC_LEVEL_PLAIN: dict[str, str] = {
    "A": "Strong evidence — drug recommendation with high confidence",
    "B": "Moderate evidence — drug recommendation with caution",
    "C": "Limited evidence — decision left to the physician",
    "D": "No specific recommendation — continue the usual protocol",
}


def summarize_report_plain(clinical_content: dict, *, patient_label: str | None = None) -> dict:
    """Convert clinical content into simple plain-language paragraphs."""
    paragraphs: list[str] = [DECISION_SUPPORT_BANNER]

    patient_ref = f"patient {patient_label}" if patient_label else "the patient"
    paragraphs.append(f"Plain summary for {patient_ref}:")

    hp = clinical_content.get("high_priority_variants") or []
    if hp:
        paragraphs.append(
            f"In the genetic test, {len(hp)} important findings were found that may affect drugs or treatment:"
        )
        for v in hp[:6]:
            gene = v.get("gene") or "unspecified gene"
            rs = v.get("rs_id") or f"{v.get('chromosome')}:{v.get('position')}"
            sig_plain = SIGNIFICANCE_PLAIN.get(
                v.get("clinical_significance", ""),
                "needs further review",
            )
            paragraphs.append(f"• {gene} ({rs}): {sig_plain}.")
    else:
        paragraphs.append(
            "No variant of high clinical significance was identified in this test. "
            "Treatment usually continues according to the standard protocol."
        )

    drugs = clinical_content.get("drug_recommendations") or []
    if drugs:
        paragraphs.append("Drug recommendations (based on the CPIC guideline):")
        for d in drugs[:8]:
            drug_name = d.get("drug_fa") or d.get("drug", "")
            level = d.get("cpic_level", "C")
            level_plain = CPIC_LEVEL_PLAIN.get(level, "")
            action = d.get("action_fa") or d.get("recommendation") or "needs physician review"
            gene = d.get("gene") or ""
            gene_part = f" (gene {gene})" if gene else ""
            paragraphs.append(f"• {drug_name}{gene_part}: {action}. {level_plain}")

    interactions = clinical_content.get("drug_interactions") or []
    if interactions:
        paragraphs.append(f"Note: {len(interactions)} possible drug interactions were identified — a review of the prescription is recommended.")

    module = clinical_content.get("module_analysis")
    if module and module.get("summary_fa"):
        paragraphs.append(f"Module analysis: {module['summary_fa']}")

    paragraphs.append(SHORT_DISCLAIMER_FA)

    return {
        "plain_summary": paragraphs,
        "plain_summary_text": "\n\n".join(paragraphs),
        "disclaimer": FULL_DISCLAIMER_FA,
        "decision_support_only": True,
        "source": "rule_based",
    }

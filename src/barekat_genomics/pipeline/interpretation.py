"""تفسیر و اولویت‌بندی واریانت‌ها با ML و دانش زیست‌شناسی."""

from dataclasses import dataclass

from barekat_genomics.ml.classifier import VariantClassifier
from barekat_genomics.pipeline.variant_calling import CalledVariant, PHARMACOGENOMIC_GENES

# نگاشت rsID به ژن و اثر فارماکوژنومیک
KNOWN_VARIANTS = {
    "rs1801133": {"gene": "MTHFR", "consequence": "missense_variant", "drug": "methotrexate"},
    "rs4244285": {"gene": "CYP2C19", "consequence": "splice_variant", "drug": "clopidogrel"},
    "rs1799853": {"gene": "CYP2C9", "consequence": "missense_variant", "drug": "warfarin"},
    "rs1142345": {"gene": "TPMT", "consequence": "missense_variant", "drug": "azathioprine"},
    "rs1800460": {"gene": "DPYD", "consequence": "missense_variant", "drug": "fluorouracil"},
}


@dataclass
class VariantInterpretation:
    gene: str | None
    consequence: str | None
    clinical_significance: str
    pharmacogenomic_effect: str | None
    priority_score: float
    ml_confidence: float
    interpretation: str


_classifier = VariantClassifier()


def interpret_variants(variants: list[CalledVariant]) -> list[tuple[CalledVariant, VariantInterpretation]]:
    results = []
    for variant in variants:
        known = KNOWN_VARIANTS.get(variant.rs_id or "", {})
        gene = known.get("gene", _infer_gene(variant))
        consequence = known.get("consequence", _infer_consequence(variant))

        features = [
            variant.quality_score,
            variant.depth,
            1.0 if variant.variant_type == "SNP" else 0.0,
            1.0 if gene in PHARMACOGENOMIC_GENES else 0.0,
            1.0 if variant.rs_id else 0.0,
        ]
        ml_score, ml_confidence = _classifier.predict(features)

        clinical_sig = _classify_clinical_significance(ml_score, gene)
        pgx_effect = _generate_pgx_effect(gene, known.get("drug"), clinical_sig)
        priority = _compute_priority(ml_score, gene, clinical_sig)
        interpretation_text = _generate_interpretation(variant, gene, clinical_sig, pgx_effect)

        results.append((
            variant,
            VariantInterpretation(
                gene=gene,
                consequence=consequence,
                clinical_significance=clinical_sig,
                pharmacogenomic_effect=pgx_effect,
                priority_score=priority,
                ml_confidence=ml_confidence,
                interpretation=interpretation_text,
            ),
        ))
    return sorted(results, key=lambda x: x[1].priority_score, reverse=True)


def generate_drug_recommendations(
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
) -> dict:
    recommendations = {}
    for _, interp in interpretations:
        if interp.pharmacogenomic_effect and interp.gene:
            drug = KNOWN_VARIANTS.get("", {}).get("drug")
            for rs_id, info in KNOWN_VARIANTS.items():
                if info.get("gene") == interp.gene:
                    drug = info["drug"]
                    break
            if drug:
                recommendations[drug] = {
                    "gene": interp.gene,
                    "significance": interp.clinical_significance,
                    "recommendation": interp.pharmacogenomic_effect,
                    "confidence": interp.ml_confidence,
                }
    return recommendations


def _infer_gene(variant: CalledVariant) -> str | None:
    if variant.rs_id and variant.rs_id in KNOWN_VARIANTS:
        return KNOWN_VARIANTS[variant.rs_id]["gene"]
    return None


def _infer_consequence(variant: CalledVariant) -> str:
    if variant.variant_type == "INDEL":
        return "frameshift_variant" if len(variant.alt_allele) != len(variant.ref_allele) else "inframe_variant"
    return "missense_variant"


def _classify_clinical_significance(ml_score: float, gene: str | None) -> str:
    if gene in PHARMACOGENOMIC_GENES and ml_score > 0.7:
        return "pathogenic"
    if ml_score > 0.5:
        return "likely_pathogenic"
    if ml_score > 0.3:
        return "uncertain_significance"
    return "benign"


def _generate_pgx_effect(gene: str | None, drug: str | None, significance: str) -> str | None:
    if not gene or significance in ("benign", "uncertain_significance"):
        return None
    drug_name = drug or "داروهای مرتبط"
    if significance == "pathogenic":
        return f"ژن {gene}: احتمال پاسخ ضعیف یا عوارض جانبی به {drug_name}. دوزاژ جایگزین توصیه می‌شود."
    return f"ژن {gene}: نیاز به پایش دقیق‌تر هنگام تجویز {drug_name}."


def _compute_priority(ml_score: float, gene: str | None, significance: str) -> float:
    base = ml_score
    if gene in PHARMACOGENOMIC_GENES:
        base += 0.2
    if significance == "pathogenic":
        base += 0.3
    elif significance == "likely_pathogenic":
        base += 0.15
    return min(base, 1.0)


def _generate_interpretation(
    variant: CalledVariant,
    gene: str | None,
    significance: str,
    pgx_effect: str | None,
) -> str:
    loc = f"{variant.chromosome}:{variant.position}"
    gene_str = f" در ژن {gene}" if gene else ""
    base = f"واریانت {variant.ref_allele}>{variant.alt_allele} در {loc}{gene_str} با اهمیت بالینی {significance}."
    if pgx_effect:
        base += f" {pgx_effect}"
    return base

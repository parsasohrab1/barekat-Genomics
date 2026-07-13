"""تفسیر واریانت با پایگاه دانش رسمی (PharmGKB, CPIC, ClinVar, gnomAD, dbSNP)."""

from dataclasses import asdict, dataclass

from barekat_genomics.knowledge import get_knowledge_registry
from barekat_genomics.knowledge.models import VariantKnowledge
from barekat_genomics.ml.features import extract_features
from barekat_genomics.ml.classifier import VariantClassifier
from barekat_genomics.pipeline.pgx_genes import PHARMACOGENOMIC_GENES
from barekat_genomics.pipeline.variant_calling import CalledVariant

# نگاشت ClinVar → اهمیت بالینی داخلی
CLINVAR_SIG_MAP = {
    "pathogenic": "pathogenic",
    "likely_pathogenic": "likely_pathogenic",
    "uncertain_significance": "uncertain_significance",
    "benign": "benign",
    "drug_response": "pathogenic",
    "risk_factor": "likely_pathogenic",
}


@dataclass
class VariantInterpretation:
    gene: str | None
    consequence: str | None
    clinical_significance: str
    pharmacogenomic_effect: str | None
    priority_score: float
    ml_confidence: float
    ml_score: float
    interpretation: str
    knowledge_sources: list[str]
    gnomad_af: float | None = None
    phenotype: str | None = None


_classifier = VariantClassifier()
_registry = get_knowledge_registry()
_cache = None


def _annotation_cache():
    global _cache
    if _cache is None:
        from barekat_genomics.services.annotation_cache_service import AnnotationCacheService

        _cache = AnnotationCacheService()
    return _cache


def interpret_variants(
    variants: list[CalledVariant],
    *,
    genome_build: str = "GRCh38",
) -> list[tuple[CalledVariant, VariantInterpretation]]:
    model_version = _classifier.active_version or "v1"
    cache = _annotation_cache()
    results = []
    for variant in variants:
        cached = cache.get(variant, genome_build=genome_build, model_version=model_version)
        if cached:
            results.append((variant, VariantInterpretation(**cached)))
            continue

        kb = _registry.lookup(variant)
        gene = variant.gene or (kb.gene if kb else None) or _infer_gene_from_kb(variant, kb)
        consequence = (
            variant.consequence
            or (kb.consequence if kb else None)
            or _infer_consequence(variant)
        )

        fv = extract_features(variant, gene, kb)
        ml_score, ml_confidence, _model_ver = _classifier.predict(
            fv, routing_key=variant.rs_id or f"{variant.chromosome}:{variant.position}"
        )

        clinical_sig = _resolve_clinical_significance(kb, ml_score, gene)
        drug = kb.drug if kb else _registry.drug_for_gene(gene)
        pgx_effect = _generate_pgx_effect(gene, drug, clinical_sig, kb)
        priority = _compute_priority(ml_score, gene, clinical_sig, kb)
        interpretation_text = _generate_interpretation(variant, gene, clinical_sig, pgx_effect, kb)
        sources = kb.sources if kb else []

        interp = VariantInterpretation(
                gene=gene,
                consequence=consequence,
                clinical_significance=clinical_sig,
                pharmacogenomic_effect=pgx_effect,
                priority_score=priority,
                ml_confidence=ml_confidence,
                ml_score=ml_score,
                interpretation=interpretation_text,
                knowledge_sources=sources,
                gnomad_af=kb.gnomad_af if kb else None,
                phenotype=kb.phenotype if kb else None,
            )
        results.append((variant, interp))
        cache.set(variant, asdict(interp), genome_build=genome_build, model_version=model_version)
    return sorted(results, key=lambda x: x[1].priority_score, reverse=True)


def generate_drug_recommendations(
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
) -> dict:
    recommendations = {}
    for variant, interp in interpretations:
        if not interp.pharmacogenomic_effect or not interp.gene:
            continue
        kb = _registry.lookup(variant)
        drug = kb.drug if kb and kb.drug else _registry.drug_for_gene(interp.gene)
        if not drug:
            continue
        cpic = _registry.get_cpic_for_gene_drug(interp.gene, drug) or {}
        recommendations[drug] = {
            "gene": interp.gene,
            "significance": interp.clinical_significance,
            "recommendation": interp.pharmacogenomic_effect,
            "confidence": interp.ml_confidence,
            "cpic_level": cpic.get("cpic_level") or (kb.cpic_level if kb else None),
            "cpic_guideline": cpic.get("guideline") or (kb.cpic_guideline if kb else None),
            "action_fa": cpic.get("action_fa") or (kb.cpic_action_fa if kb else None),
            "drug_fa": cpic.get("drug_fa") or (kb.drug_fa if kb else None),
            "phenotype": interp.phenotype or (kb.phenotype if kb else None),
            "gnomad_af": interp.gnomad_af,
            "sources": interp.knowledge_sources,
        }
    return recommendations


def _infer_gene_from_kb(variant: CalledVariant, kb: VariantKnowledge | None) -> str | None:
    if kb and kb.gene:
        return kb.gene
    return None


def _infer_consequence(variant: CalledVariant) -> str:
    if variant.variant_type == "INDEL":
        return "frameshift_variant" if len(variant.alt_allele) != len(variant.ref_allele) else "inframe_variant"
    return "missense_variant"


def _resolve_clinical_significance(
    kb: VariantKnowledge | None,
    ml_score: float,
    gene: str | None,
) -> str:
    if kb and kb.clinical_significance:
        mapped = CLINVAR_SIG_MAP.get(kb.clinical_significance, kb.clinical_significance)
        if mapped in ("pathogenic", "likely_pathogenic", "uncertain_significance", "benign"):
            return mapped
    if gene in PHARMACOGENOMIC_GENES and ml_score > 0.7:
        return "pathogenic"
    if ml_score > 0.5:
        return "likely_pathogenic"
    if ml_score > 0.3:
        return "uncertain_significance"
    return "benign"


def _generate_pgx_effect(
    gene: str | None,
    drug: str | None,
    significance: str,
    kb: VariantKnowledge | None,
) -> str | None:
    if not gene or significance in ("benign", "uncertain_significance"):
        return None
    drug_name = (kb.drug_fa if kb and kb.drug_fa else drug) or "داروهای مرتبط"
    phenotype = kb.phenotype if kb else None
    if phenotype:
        base = f"ژن {gene} ({phenotype}): "
    else:
        base = f"ژن {gene}: "
    if kb and kb.cpic_action_fa:
        return base + kb.cpic_action_fa
    if significance == "pathogenic":
        return base + f"احتمال پاسخ ضعیف یا عوارض جانبی به {drug_name}. دوزاژ جایگزین توصیه می‌شود."
    return base + f"نیاز به پایش دقیق‌تر هنگام تجویز {drug_name}."


def _compute_priority(
    ml_score: float,
    gene: str | None,
    significance: str,
    kb: VariantKnowledge | None,
) -> float:
    base = ml_score
    if gene in PHARMACOGENOMIC_GENES:
        base += 0.2
    if significance == "pathogenic":
        base += 0.3
    elif significance == "likely_pathogenic":
        base += 0.15
    if kb and kb.cpic_level == "A":
        base += 0.1
    if kb and kb.gnomad_af is not None and kb.gnomad_af < 0.05:
        base += 0.05
    return min(base, 1.0)


def _generate_interpretation(
    variant: CalledVariant,
    gene: str | None,
    significance: str,
    pgx_effect: str | None,
    kb: VariantKnowledge | None,
) -> str:
    loc = f"{variant.chromosome}:{variant.position}"
    rs = f" ({variant.rs_id})" if variant.rs_id else ""
    gene_str = f" در ژن {gene}" if gene else ""
    base = f"واریانت {variant.ref_allele}>{variant.alt_allele} در {loc}{rs}{gene_str} با اهمیت بالینی {significance}."
    if kb and kb.gnomad_af is not None:
        base += f" فراوانی gnomAD: {kb.gnomad_af:.4f}."
    if kb and kb.sources:
        base += f" منابع: {', '.join(kb.sources)}."
    if pgx_effect:
        base += f" {pgx_effect}"
    return base

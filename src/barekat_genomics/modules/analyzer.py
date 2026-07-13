"""تحلیل‌گر ماژول‌های تشخیصی."""

from __future__ import annotations

from dataclasses import dataclass, field

from barekat_genomics.modules.panels import PRS_TRAITS
from barekat_genomics.modules.registry import GenomicsModule, get_module
from barekat_genomics.pipeline.interpretation import VariantInterpretation
from barekat_genomics.pipeline.variant_calling import CalledVariant

SIGNIFICANCE_ACTIONABLE = {"pathogenic", "likely_pathogenic", "drug_response"}


@dataclass
class ModuleFinding:
    gene: str | None
    rs_id: str | None
    chromosome: str
    position: int
    clinical_significance: str
    interpretation: str | None
    priority_score: float
    ml_score: float
    category: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class ModuleAnalysisResult:
    module_id: str
    module_name_fa: str
    summary_fa: str
    findings: list[ModuleFinding]
    actionable_count: int
    panel_coverage: dict
    metadata: dict = field(default_factory=dict)


def analyze_module(
    module_id: str,
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
    *,
    normal_interpretations: list[tuple[CalledVariant, VariantInterpretation]] | None = None,
    patient_label: str | None = None,
) -> ModuleAnalysisResult:
    module = get_module(module_id)

    if module_id == "tumor_normal":
        return _analyze_tumor_normal(module, interpretations, normal_interpretations or [])
    if module_id == "prs":
        return _analyze_prs(module, interpretations, patient_label)
    if module_id in ("pharmacogenomics", "pgx_panel"):
        return _analyze_gene_panel(module, interpretations, category="pharmacogenomic")
    if module_id == "cgp":
        return _analyze_gene_panel(module, interpretations, category="oncology_actionable")
    if module_id == "carrier_screening":
        return _analyze_carrier(module, interpretations)

    return _analyze_gene_panel(module, interpretations)


def _analyze_gene_panel(
    module: GenomicsModule,
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
    *,
    category: str = "panel",
) -> ModuleAnalysisResult:
    findings: list[ModuleFinding] = []
    genes_found: set[str] = set()

    for variant, interp in interpretations:
        gene = interp.gene
        if not gene or gene not in module.genes:
            continue
        genes_found.add(gene)
        if interp.clinical_significance not in SIGNIFICANCE_ACTIONABLE and interp.ml_score <= 0.5:
            continue
        findings.append(
            ModuleFinding(
                gene=gene,
                rs_id=variant.rs_id,
                chromosome=variant.chromosome,
                position=variant.position,
                clinical_significance=interp.clinical_significance,
                interpretation=interp.interpretation,
                priority_score=interp.priority_score,
                ml_score=interp.ml_score,
                category=category,
            )
        )

    findings.sort(key=lambda f: f.priority_score, reverse=True)
    actionable = len(findings)
    covered = len(genes_found)
    total = len(module.genes)
    summary = (
        f"پنل {module.name_fa}: {actionable} واریانت actionable در {covered}/{total} ژن پوشش‌داده‌شده."
    )

    return ModuleAnalysisResult(
        module_id=module.id,
        module_name_fa=module.name_fa,
        summary_fa=summary,
        findings=findings,
        actionable_count=actionable,
        panel_coverage={
            "genes_in_panel": total,
            "genes_with_variants": covered,
            "coverage_pct": round(covered / total * 100, 1) if total else 0,
        },
        metadata={"category": category},
    )


def _analyze_carrier(
    module: GenomicsModule,
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
) -> ModuleAnalysisResult:
    findings: list[ModuleFinding] = []
    carrier_genes: set[str] = set()

    for variant, interp in interpretations:
        gene = interp.gene
        if not gene or gene not in module.genes:
            continue
        if interp.clinical_significance in ("benign", "likely_benign") and interp.ml_score < 0.3:
            continue
        carrier_genes.add(gene)
        findings.append(
            ModuleFinding(
                gene=gene,
                rs_id=variant.rs_id,
                chromosome=variant.chromosome,
                position=variant.position,
                clinical_significance=interp.clinical_significance,
                interpretation=interp.interpretation,
                priority_score=interp.priority_score,
                ml_score=interp.ml_score,
                category="carrier",
                extra={"carrier_status": _carrier_status(interp)},
            ),
        )

    findings.sort(key=lambda f: f.priority_score, reverse=True)
    summary = (
        f"غربالگری ناقل: {len(findings)} واریانت در {len(carrier_genes)} ژن — "
        f"{'نیاز به مشاوره ژنتیک' if findings else 'ناقل شناسایی نشد در پنل'}"
    )

    return ModuleAnalysisResult(
        module_id=module.id,
        module_name_fa=module.name_fa,
        summary_fa=summary,
        findings=findings,
        actionable_count=len(findings),
        panel_coverage={
            "genes_screened": len(module.genes),
            "genes_with_findings": len(carrier_genes),
        },
        metadata={"recommendation": "genetic_counseling" if findings else "routine"},
    )


def _carrier_status(interp: VariantInterpretation) -> str:
    if interp.clinical_significance in ("pathogenic", "likely_pathogenic"):
        return "likely_carrier"
    if interp.clinical_significance == "uncertain_significance":
        return "vus"
    return "negative"


def _analyze_tumor_normal(
    module: GenomicsModule,
    tumor: list[tuple[CalledVariant, VariantInterpretation]],
    normal: list[tuple[CalledVariant, VariantInterpretation]],
) -> ModuleAnalysisResult:
    normal_keys = {
        (v.chromosome, v.position, v.ref_allele, v.alt_allele) for v, _ in normal
    }
    findings: list[ModuleFinding] = []

    for variant, interp in tumor:
        key = (variant.chromosome, variant.position, variant.ref_allele, variant.alt_allele)
        in_normal = key in normal_keys
        gene = interp.gene
        if gene and gene not in module.genes:
            continue
        if in_normal and interp.clinical_significance in ("benign", "likely_benign"):
            continue

        origin = "germline" if in_normal else "somatic"
        if interp.clinical_significance in SIGNIFICANCE_ACTIONABLE or not in_normal:
            findings.append(
                ModuleFinding(
                    gene=gene,
                    rs_id=variant.rs_id,
                    chromosome=variant.chromosome,
                    position=variant.position,
                    clinical_significance=interp.clinical_significance,
                    interpretation=interp.interpretation,
                    priority_score=interp.priority_score,
                    ml_score=interp.ml_score,
                    category="somatic" if origin == "somatic" else "germline",
                    extra={"origin": origin, "in_normal": in_normal},
                ),
            )

    somatic = sum(1 for f in findings if f.extra.get("origin") == "somatic")
    germline = sum(1 for f in findings if f.extra.get("origin") == "germline")
    summary = (
        f"مقایسه تومور/نرمال: {somatic} واریانت سوماتیک، {germline} واریانت ژرم‌لاین actionable"
    )

    return ModuleAnalysisResult(
        module_id=module.id,
        module_name_fa=module.name_fa,
        summary_fa=summary,
        findings=findings,
        actionable_count=len(findings),
        panel_coverage={"somatic": somatic, "germline": germline},
        metadata={"paired_analysis": True},
    )


def _analyze_prs(
    module: GenomicsModule,
    interpretations: list[tuple[CalledVariant, VariantInterpretation]],
    patient_label: str | None,
) -> ModuleAnalysisResult:
    rs_map = {v.rs_id: (v, i) for v, i in interpretations if v.rs_id}
    trait_scores: list[dict] = []

    for trait_id, trait in PRS_TRAITS.items():
        score = 0.0
        hits = 0
        for rs_id, weight in zip(trait["snps"], trait["weights"]):
            if rs_id in rs_map:
                _, interp = rs_map[rs_id]
                score += weight * interp.ml_score
                hits += 1
        percentile = min(99, max(1, int(score * 100)))
        risk_level = "high" if percentile >= 80 else "moderate" if percentile >= 50 else "low"
        trait_scores.append({
            "trait_id": trait_id,
            "trait_fa": trait["name_fa"],
            "score": round(score, 3),
            "percentile": percentile,
            "risk_level": risk_level,
            "snps_evaluated": hits,
            "snps_total": len(trait["snps"]),
        })

    high_risk = [t for t in trait_scores if t["risk_level"] == "high"]
    summary = (
        f"PRS: {len(high_risk)} بیماری با ریسک بالا از {len(trait_scores)} ارزیابی‌شده"
        + (f" — بیمار {patient_label}" if patient_label else "")
    )

    return ModuleAnalysisResult(
        module_id=module.id,
        module_name_fa=module.name_fa,
        summary_fa=summary,
        findings=[],
        actionable_count=len(high_risk),
        panel_coverage={"traits_evaluated": len(trait_scores)},
        metadata={"prs_scores": trait_scores},
    )


def result_to_dict(result: ModuleAnalysisResult) -> dict:
    return {
        "module_id": result.module_id,
        "module_name_fa": result.module_name_fa,
        "summary_fa": result.summary_fa,
        "actionable_count": result.actionable_count,
        "panel_coverage": result.panel_coverage,
        "metadata": result.metadata,
        "findings": [
            {
                "gene": f.gene,
                "rs_id": f.rs_id,
                "chromosome": f.chromosome,
                "position": f.position,
                "clinical_significance": f.clinical_significance,
                "interpretation": f.interpretation,
                "priority_score": f.priority_score,
                "ml_score": f.ml_score,
                "category": f.category,
                **f.extra,
            }
            for f in result.findings
        ],
    }

"""هماهنگ‌کننده پایپ‌لاین کامل پردازش."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from barekat_genomics.modules.analyzer import analyze_module, result_to_dict
from barekat_genomics.modules.registry import DEFAULT_MODULE
from barekat_genomics.pipeline.alignment import align_fastq, prepare_bam
from barekat_genomics.pipeline.interpretation import (
    VariantInterpretation,
    generate_drug_recommendations,
    interpret_variants,
)
from barekat_genomics.pipeline.mode import assert_production_ready, is_production_pipeline
from barekat_genomics.pipeline.preprocessing import (
    QCMetrics,
    enrich_qc_with_bam_coverage,
    run_quality_control,
)
from barekat_genomics.pipeline.reference import sample_work_dir
from barekat_genomics.pipeline.report_builder import build_clinical_report, executive_summary_text
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants, filter_variants

StageCallback = Callable[[str], None]


@dataclass
class PipelineResult:
    qc_metrics: QCMetrics
    variants: list[CalledVariant]
    interpretations: list[tuple[CalledVariant, VariantInterpretation]]
    drug_recommendations: dict
    clinical_content: dict
    report_summary: str
    success: bool
    module_analysis: dict | None = None
    error: str | None = None
    work_dir: str | None = None


def run_full_pipeline(
    file_path: str,
    file_type: str,
    genome_build: str = "GRCh38",
    sample_label: str | None = None,
    *,
    module_id: str = DEFAULT_MODULE,
    assay_type: str = "panel",
    normal_interpretations: list | None = None,
    on_stage: StageCallback | None = None,
) -> PipelineResult:
    """
    اجرای کامل پایپ‌لاین (WGS / WES / Panel):

    FASTQ → QC → BWA → MarkDuplicates → GATK HC (-L برای WES/Panel) → SnpEff → Interpretation
    BAM   → QC → MarkDuplicates → GATK HC → SnpEff → Interpretation
    VCF   → QC سبک → annotate/parse → Interpretation  (بدون alignment)
    CRAM  → مشابه BAM در production
    """
    from barekat_genomics.pipeline.assay_config import get_assay_profile, normalize_file_type

    ft = normalize_file_type(file_type)
    profile = get_assay_profile(assay_type)
    label = sample_label or Path(file_path).stem
    work = sample_work_dir(label)

    def _stage(name: str) -> None:
        if on_stage:
            on_stage(name)

    try:
        if is_production_pipeline() and ft != "VCF":
            assert_production_ready(genome_build)

        _stage("quality_control")
        qc = run_quality_control(file_path, ft, work_dir=work)
        if not qc.passed:
            return PipelineResult(
                qc_metrics=qc,
                variants=[],
                interpretations=[],
                drug_recommendations={},
                clinical_content={},
                report_summary="نمونه در کنترل کیفیت رد شد.",
                success=False,
                error=f"QC failed: {', '.join(qc.warnings)}",
                work_dir=str(work),
            )

        bam_path: Path | None = None
        if ft == "VCF":
            _stage("alignment")  # skip — stage bookmark for UI parity
        elif ft == "FASTQ" and is_production_pipeline():
            _stage("alignment")
            bam_path = align_fastq(file_path, work, genome_build)
            qc = enrich_qc_with_bam_coverage(qc, bam_path)
        elif ft in ("BAM", "CRAM") and is_production_pipeline():
            _stage("alignment")
            bam_path = prepare_bam(file_path, work)
            qc = enrich_qc_with_bam_coverage(qc, bam_path)
        else:
            _stage("alignment")

        _stage("variant_calling")
        raw_variants = call_variants(
            file_path,
            ft,
            genome_build,
            work_dir=work / "variants",
            bam_path=bam_path,
            assay_type=profile.assay_type,
        )
        min_depth = 0 if ft == "VCF" else 10
        filtered = filter_variants(raw_variants, min_depth=min_depth)

        _stage("interpretation")
        interpretations = interpret_variants(filtered, genome_build=genome_build)
        drug_recs = generate_drug_recommendations(interpretations)

        clinical = build_clinical_report(
            interpretations,
            drug_recs,
            patient_external_id=label,
            genome_build=genome_build,
        )
        module_result = analyze_module(
            module_id,
            interpretations,
            normal_interpretations=normal_interpretations,
            patient_label=label,
        )
        module_dict = result_to_dict(module_result)
        clinical["module_analysis"] = module_dict
        clinical["assay"] = {
            "assay_type": profile.assay_type,
            "display_name": profile.display_name,
            "file_type": ft,
            "min_mean_depth": profile.min_mean_depth,
        }

        summary = executive_summary_text(clinical)
        if module_result.summary_fa:
            summary = f"{module_result.summary_fa}\n\n{summary}"

        return PipelineResult(
            qc_metrics=qc,
            variants=filtered,
            interpretations=interpretations,
            drug_recommendations=drug_recs,
            clinical_content=clinical,
            report_summary=summary,
            module_analysis=module_dict,
            success=True,
            work_dir=str(work),
        )
    except Exception as e:
        return PipelineResult(
            qc_metrics=QCMetrics(0, 0, 0, 0, False, []),
            variants=[],
            interpretations=[],
            drug_recommendations={},
            clinical_content={},
            report_summary="خطا در پردازش.",
            success=False,
            error=str(e),
            work_dir=str(work),
        )

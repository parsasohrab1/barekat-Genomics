"""هماهنگ‌کننده پایپ‌لاین کامل پردازش."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from barekat_genomics.pipeline.alignment import align_fastq, prepare_bam
from barekat_genomics.pipeline.mode import is_production_pipeline
from barekat_genomics.pipeline.preprocessing import QCMetrics, run_quality_control
from barekat_genomics.pipeline.reference import sample_work_dir
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants, filter_variants
from barekat_genomics.pipeline.interpretation import (
    VariantInterpretation,
    generate_drug_recommendations,
    interpret_variants,
)
from barekat_genomics.modules.analyzer import analyze_module, result_to_dict
from barekat_genomics.modules.registry import DEFAULT_MODULE
from barekat_genomics.pipeline.report_builder import build_clinical_report, executive_summary_text


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
    normal_interpretations: list | None = None,
) -> PipelineResult:
    """
    اجرای کامل پایپ‌لاین:

    FASTQ → FastQC/MultiQC → BWA-MEM2 → GATK HaplotypeCaller → SnpEff → Interpretation
    BAM   → samtools QC → GATK HaplotypeCaller → SnpEff → Interpretation
    """
    label = sample_label or Path(file_path).stem
    work = sample_work_dir(label)

    try:
        qc = run_quality_control(file_path, file_type, work_dir=work)
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
        if file_type == "FASTQ" and is_production_pipeline():
            bam_path = align_fastq(file_path, work, genome_build)
        elif file_type == "BAM" and is_production_pipeline():
            bam_path = prepare_bam(file_path, work)

        raw_variants = call_variants(
            file_path,
            file_type,
            genome_build,
            work_dir=work / "variants",
            bam_path=bam_path,
        )
        filtered = filter_variants(raw_variants)
        interpretations = interpret_variants(filtered, genome_build=genome_build)
        drug_recs = generate_drug_recommendations(interpretations)

        clinical = build_clinical_report(
            interpretations,
            drug_recs,
            patient_external_id=label,
        )
        module_result = analyze_module(
            module_id,
            interpretations,
            normal_interpretations=normal_interpretations,
            patient_label=label,
        )
        module_dict = result_to_dict(module_result)
        clinical["module_analysis"] = module_dict

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

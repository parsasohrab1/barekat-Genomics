"""هماهنگ‌کننده پایپ‌لاین کامل پردازش."""

from dataclasses import dataclass

from barekat_genomics.pipeline.preprocessing import QCMetrics, run_quality_control
from barekat_genomics.pipeline.variant_calling import CalledVariant, call_variants, filter_variants
from barekat_genomics.pipeline.interpretation import (
    VariantInterpretation,
    generate_drug_recommendations,
    interpret_variants,
)


@dataclass
class PipelineResult:
    qc_metrics: QCMetrics
    variants: list[CalledVariant]
    interpretations: list[tuple[CalledVariant, VariantInterpretation]]
    drug_recommendations: dict
    report_summary: str
    success: bool
    error: str | None = None


def run_full_pipeline(
    file_path: str,
    file_type: str,
    genome_build: str = "GRCh38",
) -> PipelineResult:
    """اجرای کامل پایپ‌لاین: QC → Variant Calling → Interpretation → Report."""
    try:
        qc = run_quality_control(file_path, file_type)
        if not qc.passed:
            return PipelineResult(
                qc_metrics=qc,
                variants=[],
                interpretations=[],
                drug_recommendations={},
                report_summary="نمونه در کنترل کیفیت رد شد.",
                success=False,
                error=f"QC failed: {', '.join(qc.warnings)}",
            )

        raw_variants = call_variants(file_path, file_type, genome_build)
        filtered = filter_variants(raw_variants)
        interpretations = interpret_variants(filtered)
        drug_recs = generate_drug_recommendations(interpretations)

        high_priority = [i for _, i in interpretations if i.priority_score > 0.5]
        summary = (
            f"تحلیل {len(filtered)} واریانت انجام شد. "
            f"{len(high_priority)} واریانت با اولویت بالا شناسایی شد. "
            f"{len(drug_recs)} توصیه دارویی تولید شد."
        )

        return PipelineResult(
            qc_metrics=qc,
            variants=filtered,
            interpretations=interpretations,
            drug_recommendations=drug_recs,
            report_summary=summary,
            success=True,
        )
    except Exception as e:
        return PipelineResult(
            qc_metrics=QCMetrics(0, 0, 0, 0, False, []),
            variants=[],
            interpretations=[],
            drug_recommendations={},
            report_summary="خطا در پردازش.",
            success=False,
            error=str(e),
        )

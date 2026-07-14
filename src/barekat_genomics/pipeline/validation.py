"""اعتبارسنجی پایپ‌لاین با ground truth benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from barekat_genomics.pipeline.variant_calling import CalledVariant


def _variant_key(v: dict | CalledVariant) -> str:
    from barekat_genomics.pipeline.variant_calling import CalledVariant as CV

    if isinstance(v, CV):
        if v.rs_id:
            return v.rs_id
        return f"{v.chromosome}:{v.position}:{v.ref_allele}>{v.alt_allele}"
    if v.get("rs_id"):
        return str(v["rs_id"])
    return f"{v['chromosome']}:{v['position']}:{v.get('ref_allele','')}>{v.get('alt_allele','')}"


def evaluate_variant_concordance(
    called: list,
    truth: list[dict],
    *,
    mode: str = "simulated",
) -> dict:
    """محاسبه precision / recall / F1 و تقریب sensitivity."""
    truth_keys = {_variant_key(t) for t in truth if t.get("expected_in_simulated", True)}
    called_keys = {_variant_key(v) for v in called}

    tp = truth_keys & called_keys
    fn = truth_keys - called_keys
    fp = called_keys - truth_keys

    precision = len(tp) / len(called_keys) if called_keys else 0.0
    recall = len(tp) / len(truth_keys) if truth_keys else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "true_positives": len(tp),
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "sensitivity": round(recall, 4),
        "specificity": None,
        "matched_rs_ids": sorted(tp),
        "missed_rs_ids": sorted(fn),
        "extra_rs_ids": sorted(fp),
        "mode": mode,
    }


def evaluate_simulated_benchmark() -> dict:
    """اجرای پایپ‌لاین simulated و مقایسه با PIPELINE_BENCHMARK_TRUTH."""
    from barekat_genomics.pipeline.variant_calling import call_variants, filter_variants

    try:
        from data.dev_fixtures import PIPELINE_BENCHMARK_TRUTH

        truth = PIPELINE_BENCHMARK_TRUTH
    except ImportError:
        truth = [
            {"rs_id": "rs1801133", "expected_in_simulated": True},
            {"rs_id": "rs4244285", "expected_in_simulated": True},
            {"rs_id": "rs1799853", "expected_in_simulated": True},
            {"rs_id": "rs1142345", "expected_in_simulated": True},
            {"rs_id": "rs1800460", "expected_in_simulated": True},
        ]

    called = filter_variants(call_variants("/fake/path.bam", "BAM"))
    return evaluate_variant_concordance(called, truth, mode="simulated")


def evaluate_from_vcf_against_truth(called_variants: list, truth_path: Path) -> dict:
    import json

    truth = json.loads(Path(truth_path).read_text(encoding="utf-8"))
    variants = truth.get("variants") if isinstance(truth, dict) else truth
    return evaluate_variant_concordance(called_variants, variants, mode="file")

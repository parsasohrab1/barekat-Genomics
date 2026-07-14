#!/usr/bin/env python3
"""اعتبارسنجی پایپ‌لاین با دیتاست benchmark و گزارش حساسیت/ویژگی.

Usage:
  python scripts/validate_pipeline_benchmark.py
  python scripts/validate_pipeline_benchmark.py --write docs/PIPELINE_VALIDATION.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from data.generate_synthetic import generate_benchmark_dataset  # noqa: E402
from barekat_genomics.pipeline.validation import evaluate_simulated_benchmark  # noqa: E402


def render_markdown(metrics: dict) -> str:
    lines = [
        "# Pipeline Validation Report",
        "",
        f"_Generated at {datetime.now(timezone.utc).isoformat()}_",
        "",
        "## Simulated concordance (PGx panel ground truth)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Mode | `{metrics['mode']}` |",
        f"| True positives | {metrics['true_positives']} |",
        f"| False positives | {metrics['false_positives']} |",
        f"| False negatives | {metrics['false_negatives']} |",
        f"| Precision | {metrics['precision']:.4f} |",
        f"| Recall / Sensitivity | {metrics['recall']:.4f} |",
        f"| F1 | {metrics['f1']:.4f} |",
        f"| Specificity | {metrics['specificity'] if metrics['specificity'] is not None else 'N/A (no true-negative set)'} |",
        "",
        "### Matched",
        "",
        ", ".join(metrics["matched_rs_ids"]) or "—",
        "",
        "### Missed",
        "",
        ", ".join(metrics["missed_rs_ids"]) or "—",
        "",
        "### Extra calls",
        "",
        ", ".join(metrics["extra_rs_ids"]) or "—",
        "",
        "## Acceptance gate (Phase 1)",
        "",
        "- Simulated recall (sensitivity) ≥ 0.80 for PGx truth set",
        "- Simulated precision ≥ 0.50 (extras without rsID tolerated in demo callset)",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, help="خروجی Markdown")
    parser.add_argument("--json-out", type=Path, help="خروجی JSON")
    parser.add_argument("--regenerate", action="store_true", help="تولید دوباره data/benchmark")
    args = parser.parse_args()

    if args.regenerate:
        generate_benchmark_dataset(n_samples=50, seed=42)

    metrics = evaluate_simulated_benchmark()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(render_markdown(metrics), encoding="utf-8")
        print(f"Wrote {args.write}")

    # Gate اولیه فاز ۱
    ok = metrics["sensitivity"] >= 0.8
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Train the VariantClassifier ensemble (v2) from ClinVar/PharmGKB + anonymized_training."""

import argparse
import sys
from pathlib import Path

from barekat_genomics.ml.training import train_variant_classifier


def main() -> int:
    parser = argparse.ArgumentParser(description="Train variant classifier ensemble (v2)")
    parser.add_argument(
        "--knowledge-dir",
        default="data/reference/knowledge",
        help="Path to ClinVar/PharmGKB/gnomAD/variant_scores files",
    )
    parser.add_argument("--model-dir", default="data/models", help="Path to save the model and registry")
    parser.add_argument("--version", default="v2", help="Model version (suggested: v2)")
    parser.add_argument(
        "--training-csv",
        default=None,
        help="Path to anonymized_training.csv for training/fine-tune",
    )
    parser.add_argument(
        "--fine-tune",
        action="store_true",
        help="limited fine-tune on anonymized data (light iteration)",
    )
    parser.add_argument("--promote", action="store_true", help="set as production")
    parser.add_argument("--no-augment", action="store_true", help="without data augmentation")
    parser.add_argument(
        "--no-deep-tabular",
        action="store_true",
        help="without MLP (tree ensemble only)",
    )
    parser.add_argument("--mlflow", action="store_true", help="log to MLflow (optional)")
    parser.add_argument(
        "--no-baseline-compare",
        action="store_true",
        help="without comparison to the RF baseline",
    )
    args = parser.parse_args()

    knowledge_dir = Path(args.knowledge_dir)
    model_dir = Path(args.model_dir)
    training_csv = Path(args.training_csv) if args.training_csv else None

    if not knowledge_dir.is_dir():
        print(f"Error: {knowledge_dir} not found", file=sys.stderr)
        return 1
    if training_csv is not None and not training_csv.is_file():
        print(f"Error: {training_csv} not found", file=sys.stderr)
        return 1

    _, metrics, registry = train_variant_classifier(
        knowledge_dir,
        model_dir=model_dir,
        version=args.version,
        promote=args.promote,
        augment=not args.no_augment,
        training_csv=training_csv,
        fine_tune=args.fine_tune,
        deep_tabular=not args.no_deep_tabular,
        compare_baseline=not args.no_baseline_compare,
        log_mlflow=args.mlflow,
    )

    summary = model_dir / f"train_summary_{args.version}.json"
    print(f"Version: {args.version}")
    print(f"production: {registry.production_version}")
    print(f"metrics: {metrics.to_dict()}")
    if summary.is_file():
        print(f"summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

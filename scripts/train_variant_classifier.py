#!/usr/bin/env python3
"""آموزش VariantClassifier ensemble (v2) از ClinVar/PharmGKB + anonymized_training."""

import argparse
import sys
from pathlib import Path

from barekat_genomics.ml.training import train_variant_classifier


def main() -> int:
    parser = argparse.ArgumentParser(description="Train variant classifier ensemble (v2)")
    parser.add_argument(
        "--knowledge-dir",
        default="data/reference/knowledge",
        help="مسیر فایل‌های ClinVar/PharmGKB/gnomAD/variant_scores",
    )
    parser.add_argument("--model-dir", default="data/models", help="مسیر ذخیره مدل و registry")
    parser.add_argument("--version", default="v2", help="نسخه مدل (پیشنهاد: v2)")
    parser.add_argument(
        "--training-csv",
        default=None,
        help="مسیر anonymized_training.csv برای آموزش/fine-tune",
    )
    parser.add_argument(
        "--fine-tune",
        action="store_true",
        help="fine-tune محدود روی داده ناشناس (تکرار سبک)",
    )
    parser.add_argument("--promote", action="store_true", help="تنظیم به‌عنوان production")
    parser.add_argument("--no-augment", action="store_true", help="بدون data augmentation")
    parser.add_argument(
        "--no-deep-tabular",
        action="store_true",
        help="بدون MLP (فقط tree ensemble)",
    )
    parser.add_argument("--mlflow", action="store_true", help="لاگ به MLflow (اختیاری)")
    parser.add_argument(
        "--no-baseline-compare",
        action="store_true",
        help="بدون مقایسه با baseline RF",
    )
    args = parser.parse_args()

    knowledge_dir = Path(args.knowledge_dir)
    model_dir = Path(args.model_dir)
    training_csv = Path(args.training_csv) if args.training_csv else None

    if not knowledge_dir.is_dir():
        print(f"خطا: {knowledge_dir} یافت نشد", file=sys.stderr)
        return 1
    if training_csv is not None and not training_csv.is_file():
        print(f"خطا: {training_csv} یافت نشد", file=sys.stderr)
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
    print(f"نسخه: {args.version}")
    print(f"production: {registry.production_version}")
    print(f"metrics: {metrics.to_dict()}")
    if summary.is_file():
        print(f"summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

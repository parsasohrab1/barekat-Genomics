#!/usr/bin/env python3
"""آموزش VariantClassifier از ClinVar + PharmGKB با ارزیابی hold-out."""

import argparse
import sys
from pathlib import Path

from barekat_genomics.ml.training import train_variant_classifier


def main() -> int:
    parser = argparse.ArgumentParser(description="Train variant classifier ensemble")
    parser.add_argument(
        "--knowledge-dir",
        default="data/reference/knowledge",
        help="مسیر فایل‌های ClinVar/PharmGKB/gnomAD/variant_scores",
    )
    parser.add_argument("--model-dir", default="data/models", help="مسیر ذخیره مدل و registry")
    parser.add_argument("--version", default="v1", help="نسخه مدل")
    parser.add_argument("--promote", action="store_true", help="تنظیم به‌عنوان production")
    parser.add_argument("--no-augment", action="store_true", help="بدون data augmentation")
    args = parser.parse_args()

    knowledge_dir = Path(args.knowledge_dir)
    model_dir = Path(args.model_dir)

    if not knowledge_dir.is_dir():
        print(f"خطا: {knowledge_dir} یافت نشد", file=sys.stderr)
        return 1

    _, metrics, registry = train_variant_classifier(
        knowledge_dir,
        model_dir=model_dir,
        version=args.version,
        promote=args.promote,
        augment=not args.no_augment,
    )

    print(f"نسخه: {args.version}")
    print(f"production: {registry.production_version}")
    print(f"metrics: {metrics.to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

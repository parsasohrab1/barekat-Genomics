"""تولید داده‌های سنتتیک ژنومیکس و فارماکوژنومیکس.

خروجی‌ها:
  - synthetic_genomics.csv       — دیتاست کامل با Copula LD
  - benchmark/pipeline_*.csv/json — ground truth برای تست پایپ‌لاین
  - training/anonymized_*.csv    — داده ناشناس برای آموزش مدل ML
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data.dev_fixtures import KNOWN_PGX_SNPS, PGX_SNPS_ORDERED, PIPELINE_BENCHMARK_TRUTH
from data.ld_copula import (
    build_ld_correlation_matrix,
    build_pgx_ld_matrix,
    pairwise_ld_r2,
    simulate_genotypes_gaussian_copula,
)

DATA_DIR = Path(__file__).resolve().parent
DEFAULT_SALT = "barekat-synthetic-v1"


def _drug_response_from_genotypes(
    genotype_row: dict[str, int],
    rng: np.random.Generator,
) -> tuple[int, float]:
    """فنوتیپ پاسخ دارو از ژنوتیپ‌های کلیدی."""
    risk = 0.0
    cyp2c19 = genotype_row.get("rs4244285", genotype_row.get("SNP_3", 0))
    cyp2c9 = genotype_row.get("rs1799853", genotype_row.get("SNP_4", 0))
    if cyp2c19 == 2:
        risk += 0.35
    elif cyp2c19 == 1:
        risk += 0.12
    if cyp2c9 == 2:
        risk += 0.25
    elif cyp2c9 == 1:
        risk += 0.10
    prob = float(np.clip(0.75 - risk, 0.08, 0.92))
    return int(rng.binomial(1, prob)), prob


def generate_synthetic_genomics_data(
    n_samples: int = 1000,
    n_snps: int = 50,
    *,
    seed: int = 42,
    use_copula: bool = True,
    block_size: int = 4,
) -> pd.DataFrame:
    """
    تولید داده‌های سنتتیک با Gaussian Copula برای LD واقعی‌تر.

    پارامترها:
        n_samples: تعداد نمونه‌ها
        n_snps: تعداد SNPهای عمومی (علاوه بر rsIDهای PharmGKB)
        use_copula: استفاده از Copula (پیش‌فرض)؛ False = HWE مستقل
    """
    rng = np.random.default_rng(seed)

    age = rng.normal(55, 15, n_samples).astype(int)
    age = np.clip(age, 18, 90)
    gender = rng.choice(["Male", "Female"], n_samples, p=[0.48, 0.52])

    mafs = rng.uniform(0.05, 0.40, n_snps).tolist()
    if use_copula:
        corr = build_ld_correlation_matrix(n_snps, block_size=block_size)
        snp_matrix = simulate_genotypes_gaussian_copula(
            n_samples, mafs, corr, seed=seed
        )
    else:
        snp_matrix = np.zeros((n_samples, n_snps), dtype=int)
        for j, maf in enumerate(mafs):
            p, q = maf, 1 - maf
            probs = [q**2, 2 * p * q, p**2]
            snp_matrix[:, j] = rng.choice([0, 1, 2], n_samples, p=probs)

    snp_data = {f"SNP_{i + 1}": snp_matrix[:, i] for i in range(n_snps)}

    # SNPهای PharmGKB با LD واقعی‌تر (بلوک جدا)
    pgx_corr, pgx_rsids, pgx_mafs = build_pgx_ld_matrix()
    pgx_matrix = simulate_genotypes_gaussian_copula(
        n_samples, pgx_mafs, pgx_corr, seed=seed + 1
    )

    drug_responses = []
    response_probs = []
    for i in range(n_samples):
        row = {rsid: int(pgx_matrix[i, j]) for j, rsid in enumerate(pgx_rsids)}
        row.update({f"SNP_{k + 1}": int(snp_matrix[i, k]) for k in range(min(5, n_snps))})
        dr, prob = _drug_response_from_genotypes(row, rng)
        drug_responses.append(dr)
        response_probs.append(prob)

    df = pd.DataFrame({
        "Patient_ID": [f"P{str(i).zfill(4)}" for i in range(n_samples)],
        "Age": age,
        "Gender": gender,
        "Drug_Response": drug_responses,
        "Response_Probability": np.round(response_probs, 3),
    })

    for col, values in snp_data.items():
        df[col] = values

    for j, rsid in enumerate(pgx_rsids):
        df[rsid] = pgx_matrix[:, j]

    df.loc[df["Age"] < 30, "Drug_Response"] = 0
    noise_idx = rng.choice(n_samples, size=max(1, int(n_samples * 0.05)), replace=False)
    df.loc[noise_idx, "Drug_Response"] = 1 - df.loc[noise_idx, "Drug_Response"]

    return df


def generate_benchmark_dataset(
    n_samples: int = 50,
    *,
    seed: int = 42,
    output_dir: Path | None = None,
) -> dict:
    """
    دیتاست benchmark با ground truth برای تست پایپ‌لاین simulated.

    خروجی:
      - pipeline_benchmark_samples.csv  — ژنوتیپ نمونه‌ها
      - pipeline_ground_truth.json      — واریانت‌های مورد انتظار
      - pipeline_expected_counts.json   — آمار خلاصه
    """
    out = output_dir or DATA_DIR / "benchmark"
    out.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_genomics_data(
        n_samples=n_samples, n_snps=10, seed=seed, use_copula=True, block_size=3
    )
    rsid_cols = [s["rsid"] for s in PGX_SNPS_ORDERED]
    sample_df = df[["Patient_ID", "Age", "Gender", "Drug_Response"] + rsid_cols].copy()
    sample_df["sample_id"] = sample_df["Patient_ID"].str.replace("P", "BENCH-", regex=False)
    sample_df["file_type"] = "BAM"
    sample_df["genome_build"] = "GRCh38"

    samples_path = out / "pipeline_benchmark_samples.csv"
    sample_df.to_csv(samples_path, index=False)

    ground_truth = {
        "version": "1.0",
        "pipeline_mode": "simulated",
        "n_samples": n_samples,
        "expected_variant_count": len(PIPELINE_BENCHMARK_TRUTH),
        "variants": PIPELINE_BENCHMARK_TRUTH,
        "notes_fa": (
            "در حالت simulated، پایپ‌لاین باید حداقل این rsIDها را برگرداند. "
            "ژنوتیپ‌های نمونه برای اعتبارسنجی cross-check هستند."
        ),
    }
    truth_path = out / "pipeline_ground_truth.json"
    truth_path.write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {
        "samples": n_samples,
        "pgx_snps": len(rsid_cols),
        "expected_pipeline_variants": len(PIPELINE_BENCHMARK_TRUTH),
        "mean_drug_response_rate": float(df["Drug_Response"].mean()),
    }
    counts_path = out / "pipeline_expected_counts.json"
    counts_path.write_text(json.dumps(counts, indent=2), encoding="utf-8")

    return {
        "samples_path": str(samples_path),
        "ground_truth_path": str(truth_path),
        "counts_path": str(counts_path),
        "ground_truth": ground_truth,
    }


def anonymize_for_training(
    df: pd.DataFrame,
    *,
    salt: str = DEFAULT_SALT,
    drop_age_exact: bool = True,
) -> pd.DataFrame:
    """
    ناشناس‌سازی برای آموزش مدل — بدون PHI قابل‌شناسایی.

    - Patient_ID → sample_hash (SHA-256)
    - Age → age_bin
    - حذف Gender در صورت نیاز (نگه می‌داریم به صورت باینری برای ML)
    """
    out = df.copy()

    out["sample_hash"] = out["Patient_ID"].apply(
        lambda pid: hashlib.sha256(f"{salt}:{pid}".encode()).hexdigest()[:16]
    )
    out = out.drop(columns=["Patient_ID"])

    if drop_age_exact and "Age" in out.columns:
        out["age_bin"] = pd.cut(
            out["Age"],
            bins=[0, 40, 60, 100],
            labels=["young", "middle", "senior"],
            include_lowest=True,
        )
        out["age_bin_code"] = out["age_bin"].cat.codes
        out = out.drop(columns=["Age", "age_bin"])

    if "Gender" in out.columns:
        out["gender_code"] = (out["Gender"] == "Male").astype(int)
        out = out.drop(columns=["Gender"])

    return out


def generate_training_dataset(
    n_samples: int = 2000,
    *,
    seed: int = 42,
    output_dir: Path | None = None,
    salt: str = DEFAULT_SALT,
) -> dict:
    """
    دیتاست ناشناس برای آموزش VariantClassifier و مدل‌های ML.

    خروجی:
      - anonymized_training.csv   — فیچر + برچسب
      - training_manifest.json    — متادیتا و هش نمونه‌ها
    """
    out = output_dir or DATA_DIR / "training"
    out.mkdir(parents=True, exist_ok=True)

    raw = generate_synthetic_genomics_data(n_samples=n_samples, n_snps=30, seed=seed)
    anon = anonymize_for_training(raw, salt=salt)

    rsid_cols = [s["rsid"] for s in PGX_SNPS_ORDERED]
    snp_cols = [c for c in anon.columns if c.startswith("SNP_")]
    feature_cols = rsid_cols + snp_cols + ["gender_code", "age_bin_code", "Response_Probability"]

    # برچسب: پاسخ دارو (قابل جایگزینی با pathogenic از ClinVar در production)
    training_df = anon[feature_cols + ["Drug_Response", "sample_hash"]].copy()
    training_df = training_df.rename(columns={"Drug_Response": "label"})

    csv_path = out / "anonymized_training.csv"
    training_df.to_csv(csv_path, index=False)

    manifest = {
        "version": "1.0",
        "n_samples": n_samples,
        "n_features": len(feature_cols),
        "feature_columns": feature_cols,
        "label_column": "label",
        "salt_prefix": salt[:8] + "...",
        "phi_removed": ["Patient_ID", "Age", "Gender"],
        "purpose": "ML model training — no re-identification intended",
    }
    manifest_path = out / "training_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "training_path": str(csv_path),
        "manifest_path": str(manifest_path),
        "n_samples": n_samples,
        "n_features": len(feature_cols),
    }


def validate_ld_structure(df: pd.DataFrame, min_block_r2: float = 0.02) -> dict:
    """اعتبارسنجی: SNPهای هم‌بلوک باید r² بالاتر از SNPهای مستقل داشته باشند."""
    rsids = [s["rsid"] for s in PGX_SNPS_ORDERED if s["rsid"] in df.columns]
    if len(rsids) < 2:
        return {"valid": True, "reason": "insufficient_snps"}

    matrix = df[rsids].to_numpy()
    r2 = pairwise_ld_r2(matrix)
    block_map = {s["rsid"]: s["ld_block"] for s in PGX_SNPS_ORDERED}

    within_r2: list[float] = []
    between_r2: list[float] = []
    for i, ri in enumerate(rsids):
        for j, rj in enumerate(rsids):
            if i >= j:
                continue
            if block_map[ri] == block_map[rj]:
                within_r2.append(r2[i, j])
            else:
                between_r2.append(r2[i, j])

    mean_within = float(np.mean(within_r2)) if within_r2 else 0.0
    mean_between = float(np.mean(between_r2)) if between_r2 else 0.0
    return {
        "valid": mean_within >= mean_between,
        "mean_r2_within_block": round(mean_within, 4),
        "mean_r2_between_block": round(mean_between, 4),
        "min_block_r2_threshold": min_block_r2,
    }


def main() -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="تولید داده سنتتیک barekat Genomics")
    parser.add_argument(
        "--mode",
        choices=["all", "full", "benchmark", "training"],
        default="all",
        help="full=CSV کامل | benchmark=تست پایپ‌لاین | training=ML ناشناس",
    )
    parser.add_argument("-n", "--samples", type=int, default=500, help="تعداد نمونه")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-copula", action="store_true", help="HWE مستقل بدون LD")
    args = parser.parse_args()

    if args.mode in ("all", "full"):
        print("==> تولید دیتاست کامل (Copula LD)...")
        genomics_data = generate_synthetic_genomics_data(
            n_samples=args.samples,
            n_snps=20,
            seed=args.seed,
            use_copula=not args.no_copula,
        )
        ld_check = validate_ld_structure(genomics_data)
        print(f"  LD validation: within={ld_check['mean_r2_within_block']}, "
              f"between={ld_check['mean_r2_between_block']}, valid={ld_check['valid']}")

        output_path = DATA_DIR / "synthetic_genomics.csv"
        genomics_data.to_csv(output_path, index=False)
        print(f"  ذخیره: {output_path} ({len(genomics_data)} رکورد)")

    if args.mode in ("all", "benchmark"):
        print("==> تولید benchmark پایپ‌لاین...")
        bench = generate_benchmark_dataset(n_samples=min(args.samples, 100), seed=args.seed)
        print(f"  نمونه‌ها: {bench['samples_path']}")
        print(f"  ground truth: {bench['ground_truth_path']}")

    if args.mode in ("all", "training"):
        print("==> تولید دیتاست ناشناس آموزش...")
        train = generate_training_dataset(n_samples=max(args.samples, 1000), seed=args.seed)
        print(f"  training: {train['training_path']} ({train['n_features']} features)")

    print("==> انجام شد.")


if __name__ == "__main__":
    main()

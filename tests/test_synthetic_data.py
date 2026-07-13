"""Tests for synthetic data generation."""

import json
from pathlib import Path

import pandas as pd

from data.dev_fixtures import PGX_SNPS_ORDERED, PIPELINE_BENCHMARK_TRUTH
from data.generate_synthetic import (
    anonymize_for_training,
    generate_benchmark_dataset,
    generate_synthetic_genomics_data,
    generate_training_dataset,
    validate_ld_structure,
)
from data.ld_copula import build_ld_correlation_matrix, simulate_genotypes_gaussian_copula


def test_generate_synthetic_data():
    df = generate_synthetic_genomics_data(n_samples=100, n_snps=10)
    assert len(df) == 100
    assert "Patient_ID" in df.columns
    assert "Drug_Response" in df.columns
    assert "SNP_1" in df.columns
    assert "SNP_10" in df.columns
    assert df["Age"].min() >= 18
    assert set(df["Drug_Response"].unique()).issubset({0, 1})


def test_snp_columns_count():
    df = generate_synthetic_genomics_data(n_samples=50, n_snps=20)
    snp_cols = [c for c in df.columns if c.startswith("SNP_")]
    assert len(snp_cols) == 20


def test_pgx_rsid_columns_present():
    df = generate_synthetic_genomics_data(n_samples=30, n_snps=5)
    for s in PGX_SNPS_ORDERED:
        assert s["rsid"] in df.columns


def test_copula_ld_higher_within_blocks():
    df = generate_synthetic_genomics_data(n_samples=500, n_snps=20, use_copula=True)
    ld = validate_ld_structure(df)
    assert ld["mean_r2_within_block"] >= ld["mean_r2_between_block"]


def test_copula_genotypes_valid_range():
    corr = build_ld_correlation_matrix(8, block_size=4)
    mafs = [0.1, 0.2, 0.15, 0.3, 0.05, 0.25, 0.12, 0.18]
    g = simulate_genotypes_gaussian_copula(200, mafs, corr, seed=1)
    assert g.shape == (200, 8)
    assert g.min() >= 0 and g.max() <= 2


def test_anonymize_removes_patient_id():
    raw = generate_synthetic_genomics_data(n_samples=20, n_snps=5)
    anon = anonymize_for_training(raw)
    assert "Patient_ID" not in anon.columns
    assert "sample_hash" in anon.columns
    assert anon["sample_hash"].nunique() == 20


def test_benchmark_dataset_files(tmp_path):
    result = generate_benchmark_dataset(n_samples=10, seed=42, output_dir=tmp_path)
    assert Path(result["samples_path"]).is_file()
    assert Path(result["ground_truth_path"]).is_file()

    truth = json.loads(Path(result["ground_truth_path"]).read_text(encoding="utf-8"))
    assert truth["expected_variant_count"] == len(PIPELINE_BENCHMARK_TRUTH)
    assert len(truth["variants"]) >= 5

    samples = pd.read_csv(result["samples_path"])
    assert "sample_id" in samples.columns
    assert "rs4244285" in samples.columns


def test_training_dataset(tmp_path):
    result = generate_training_dataset(n_samples=50, seed=42, output_dir=tmp_path)
    df = pd.read_csv(result["training_path"])
    assert "sample_hash" in df.columns
    assert "label" in df.columns
    assert "Patient_ID" not in df.columns
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["phi_removed"] == ["Patient_ID", "Age", "Gender"]


def test_pipeline_benchmark_matches_simulated_variants():
    """ground truth باید با simulated variant calling هم‌خوان باشد."""
    from barekat_genomics.pipeline.variant_calling import call_variants

    simulated_rsids = {v.rs_id for v in call_variants("/fake.bam", "BAM") if v.rs_id}
    expected_rsids = {v["rs_id"] for v in PIPELINE_BENCHMARK_TRUTH if v["expected_in_simulated"]}
    assert expected_rsids.issubset(simulated_rsids)

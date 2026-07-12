"""Tests for synthetic data generation."""

import pandas as pd

from data.generate_synthetic import generate_synthetic_genomics_data


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

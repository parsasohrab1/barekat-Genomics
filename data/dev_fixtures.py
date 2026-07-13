"""داده‌های سنتتیک توسعه — هم‌راستا با پایگاه دانش PharmGKB."""

from __future__ import annotations

# SNPهای شناخته‌شده در pharmgkb.tsv و simulated pipeline
KNOWN_PGX_SNPS: dict[str, dict] = {
    "rs1801133": {"gene": "MTHFR", "drug": "methotrexate", "snp_key": "SNP_MTHFR"},
    "rs4244285": {"gene": "CYP2C19", "drug": "clopidogrel", "snp_key": "SNP_CYP2C19"},
    "rs1799853": {"gene": "CYP2C9", "drug": "warfarin", "snp_key": "SNP_CYP2C9"},
    "rs1142345": {"gene": "TPMT", "drug": "azathioprine", "snp_key": "SNP_TPMT"},
    "rs1800460": {"gene": "DPYD", "drug": "fluorouracil", "snp_key": "SNP_DPYD"},
}

# ترتیب و پارامترهای LD برای Copula
PGX_SNPS_ORDERED: list[dict] = [
    {"rsid": "rs1801133", "gene": "MTHFR", "maf": 0.35, "ld_block": 0, "chrom": "chr1", "pos": 11796321},
    {"rsid": "rs1800460", "gene": "DPYD", "maf": 0.02, "ld_block": 0, "chrom": "chr1", "pos": 97915614},
    {"rsid": "rs4244285", "gene": "CYP2C19", "maf": 0.15, "ld_block": 1, "chrom": "chr10", "pos": 96521657},
    {"rsid": "rs1799853", "gene": "CYP2C9", "maf": 0.08, "ld_block": 1, "chrom": "chr10", "pos": 96741053},
    {"rsid": "rs1142345", "gene": "TPMT", "maf": 0.02, "ld_block": 2, "chrom": "chr6", "pos": 18130918},
]

# Ground truth برای benchmark پایپ‌لاین (حالت simulated)
PIPELINE_BENCHMARK_TRUTH: list[dict] = [
    {
        "rs_id": "rs1801133",
        "chromosome": "chr1",
        "position": 11796321,
        "ref_allele": "G",
        "alt_allele": "A",
        "gene": "MTHFR",
        "expected_in_simulated": True,
    },
    {
        "rs_id": "rs4244285",
        "chromosome": "chr10",
        "position": 96521657,
        "ref_allele": "C",
        "alt_allele": "T",
        "gene": "CYP2C19",
        "expected_in_simulated": True,
    },
    {
        "rs_id": "rs1799853",
        "chromosome": "chr10",
        "position": 96741053,
        "ref_allele": "C",
        "alt_allele": "T",
        "gene": "CYP2C9",
        "expected_in_simulated": True,
    },
    {
        "rs_id": "rs1142345",
        "chromosome": "chr22",
        "position": 42522613,
        "ref_allele": "G",
        "alt_allele": "A",
        "gene": "TPMT",
        "expected_in_simulated": True,
    },
    {
        "rs_id": "rs1800460",
        "chromosome": "chr1",
        "position": 97915614,
        "ref_allele": "C",
        "alt_allele": "T",
        "gene": "DPYD",
        "expected_in_simulated": True,
    },
]

DEV_PATIENTS = [
    {"external_id": "DEV-P001", "age": 58, "gender": "Male", "clinical_notes": "بیمار توسعه — فارماکوژنومیک"},
    {"external_id": "DEV-P002", "age": 42, "gender": "Female", "clinical_notes": "بیمار توسعه — غربالگری ناقل"},
    {"external_id": "DEV-P003", "age": 65, "gender": "Male", "clinical_notes": "بیمار توسعه — CGP"},
]

DEV_SAMPLES = [
    {"sample_id": "DEV-S001", "patient_external_id": "DEV-P001", "file_type": "BAM", "module": "pharmacogenomics"},
    {"sample_id": "DEV-S002", "patient_external_id": "DEV-P002", "file_type": "BAM", "module": "carrier_screening"},
    {"sample_id": "DEV-S003", "patient_external_id": "DEV-P003", "file_type": "BAM", "module": "cgp"},
]

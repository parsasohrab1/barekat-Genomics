"""شناسایی واریانت‌ها (SNP/Indel)."""

from dataclasses import dataclass


@dataclass
class CalledVariant:
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    variant_type: str
    quality_score: float
    depth: int
    rs_id: str | None = None


# ژن‌های فارماکوژنومیک شناخته‌شده
PHARMACOGENOMIC_GENES = {
    "CYP2D6", "CYP2C19", "CYP2C9", "TPMT", "DPYD",
    "SLCO1B1", "VKORC1", "UGT1A1", "HLA-B",
}


def call_variants(file_path: str, file_type: str, genome_build: str = "GRCh38") -> list[CalledVariant]:
    """
    شناسایی واریانت‌ها از فایل هم‌ترازشده.

    در محیط تولید با GATK HaplotypeCaller یا FreeBayes یکپارچه می‌شود.
    """
    simulated_variants = [
        CalledVariant("chr1", 11796321, "G", "A", "SNP", 99.5, 45, "rs1801133"),
        CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.2, 38, "rs4244285"),
        CalledVariant("chr19", 40991272, "C", "T", "SNP", 97.8, 42, "rs1799853"),
        CalledVariant("chr22", 42522613, "G", "A", "SNP", 96.5, 35, "rs1142345"),
        CalledVariant("chr1", 97915614, "C", "T", "SNP", 95.1, 30, "rs1800460"),
        CalledVariant("chr12", 21178615, "G", "A", "SNP", 94.3, 28, None),
        CalledVariant("chr6", 31356726, "T", "TC", "INDEL", 88.7, 22, None),
    ]
    return simulated_variants


def filter_variants(
    variants: list[CalledVariant],
    min_quality: float = 30.0,
    min_depth: int = 10,
) -> list[CalledVariant]:
    return [v for v in variants if v.quality_score >= min_quality and v.depth >= min_depth]

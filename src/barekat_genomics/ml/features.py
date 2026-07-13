"""استخراج ویژگی برای مدل طبقه‌بندی واریانت."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from barekat_genomics.knowledge.models import VariantKnowledge
from barekat_genomics.pipeline.pgx_genes import PHARMACOGENOMIC_GENES

FEATURE_NAMES: list[str] = [
    "quality_norm",
    "depth_norm",
    "is_snp",
    "is_pgx_gene",
    "has_rsid",
    "gnomad_af",
    "cadd_norm",
    "sift_deleterious",
    "polyphen_damage",
    "phylop_norm",
    "pharmgkb_strength",
    "clinvar_pathogenicity",
]


class VariantLike(Protocol):
    quality_score: float
    depth: int
    variant_type: str
    rs_id: str | None


@dataclass
class FeatureVector:
    values: list[float]
    names: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.names is None:
            self.names = FEATURE_NAMES

    def to_list(self) -> list[float]:
        return self.values


def _norm_quality(q: float) -> float:
    return min(max(q / 100.0, 0.0), 1.0)


def _norm_depth(d: float) -> float:
    return min(max(d / 100.0, 0.0), 1.0)


def _pharmgkb_strength(pgx_level: str | None) -> float:
    if not pgx_level:
        return 0.0
    level = pgx_level.strip().upper()
    if level in ("1A", "A"):
        return 1.0
    if level in ("1B", "B"):
        return 0.8
    if level in ("2A", "2B", "C"):
        return 0.5
    return 0.3


def _clinvar_pathogenicity(sig: str | None) -> float:
    if not sig:
        return 0.5
    mapping = {
        "pathogenic": 1.0,
        "likely_pathogenic": 0.85,
        "drug_response": 0.9,
        "risk_factor": 0.7,
        "uncertain_significance": 0.5,
        "benign": 0.1,
        "likely_benign": 0.15,
    }
    return mapping.get(sig.lower().replace(" ", "_"), 0.5)


def extract_features(
    variant: VariantLike,
    gene: str | None,
    kb: VariantKnowledge | None = None,
) -> FeatureVector:
    kb = kb or VariantKnowledge()
    cadd = kb.cadd_phred if kb.cadd_phred is not None else 15.0
    sift = kb.sift_score if kb.sift_score is not None else 0.5
    polyphen = kb.polyphen_score if kb.polyphen_score is not None else 0.5
    phylop = kb.phylop_score if kb.phylop_score is not None else 2.0

    values = [
        _norm_quality(variant.quality_score),
        _norm_depth(float(variant.depth)),
        1.0 if variant.variant_type == "SNP" else 0.0,
        1.0 if gene in PHARMACOGENOMIC_GENES else 0.0,
        1.0 if variant.rs_id else 0.0,
        kb.gnomad_af if kb.gnomad_af is not None else 0.01,
        min(cadd / 40.0, 1.0),
        1.0 - min(max(sift, 0.0), 1.0),
        min(max(polyphen, 0.0), 1.0),
        min(max(phylop / 10.0, 0.0), 1.0),
        _pharmgkb_strength(kb.pgx_level),
        _clinvar_pathogenicity(kb.clinical_significance),
    ]
    return FeatureVector(values=values)

"""پیکربندی assay: WGS / WES / Panel در یک workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from barekat_genomics.core.config import get_settings

ASSAY_TYPES = ("wgs", "wes", "panel")
FILE_TYPES = ("FASTQ", "BAM", "VCF", "CRAM")


@dataclass(frozen=True)
class AssayProfile:
    assay_type: str
    display_name: str
    min_mean_depth: float
    target_bed: str | None
    skip_alignment_for_vcf: bool = True
    haplotyper_intervals: bool = False
    estimated_cpu_hours: float = 1.0
    estimated_usd: float = 0.5


ASSAY_PROFILES: dict[str, AssayProfile] = {
    "wgs": AssayProfile(
        assay_type="wgs",
        display_name="Whole Genome Sequencing",
        min_mean_depth=20.0,
        target_bed=None,
        haplotyper_intervals=False,
        estimated_cpu_hours=12.0,
        estimated_usd=8.0,
    ),
    "wes": AssayProfile(
        assay_type="wes",
        display_name="Whole Exome Sequencing",
        min_mean_depth=50.0,
        target_bed="exome",
        haplotyper_intervals=True,
        estimated_cpu_hours=4.0,
        estimated_usd=2.5,
    ),
    "panel": AssayProfile(
        assay_type="panel",
        display_name="Targeted Gene Panel",
        min_mean_depth=100.0,
        target_bed="pgx_panel",
        haplotyper_intervals=True,
        estimated_cpu_hours=0.5,
        estimated_usd=0.4,
    ),
}


def get_assay_profile(assay_type: str | None) -> AssayProfile:
    key = (assay_type or "panel").lower()
    if key not in ASSAY_PROFILES:
        raise ValueError(f"assay_type نامعتبر: {assay_type} — مجاز: {', '.join(ASSAY_TYPES)}")
    return ASSAY_PROFILES[key]


def resolve_target_bed(assay_type: str) -> Path | None:
    profile = get_assay_profile(assay_type)
    if not profile.target_bed:
        return None
    settings = get_settings()
    base = Path(settings.reference_dir) / "targets"
    candidate = base / f"{profile.target_bed}.bed"
    if candidate.is_file():
        return candidate
    # مسیر نسبی پروژه
    repo = Path(__file__).resolve().parents[3] / "data" / "reference" / "targets" / f"{profile.target_bed}.bed"
    return repo if repo.is_file() else None


def normalize_file_type(file_type: str) -> str:
    ft = file_type.upper()
    if ft not in FILE_TYPES:
        raise ValueError(f"file_type نامعتبر: {file_type}")
    return ft

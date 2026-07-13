"""مسیرهای مرجع ژنوم و پیکربندی ابزارها."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from barekat_genomics.core.config import get_settings


@dataclass
class ReferenceBundle:
    genome_build: str
    reference_dir: Path
    ref_fasta: Path
    bwa_index_prefix: Path
    snpeff_db: str
    dbsnp_vcf: Path | None
    clinvar_vcf: Path | None
    pharmgkb_dir: Path | None

    @property
    def reference_ready(self) -> bool:
        return self.ref_fasta.is_file() and self.bwa_index_prefix.with_suffix(".amb").is_file()


def get_reference_bundle(genome_build: str | None = None) -> ReferenceBundle:
    settings = get_settings()
    build = genome_build or settings.genome_build
    ref_dir = Path(settings.reference_dir)

    ref_fasta = Path(settings.ref_fasta) if settings.ref_fasta else ref_dir / f"{build}.fa"
    bwa_prefix = Path(settings.bwa_index_prefix) if settings.bwa_index_prefix else ref_dir / build / build

    dbsnp = Path(settings.dbsnp_path) if settings.dbsnp_path else None
    clinvar = Path(settings.clinvar_path) if settings.clinvar_path else ref_dir / "clinvar" / "clinvar.vcf.gz"
    pharmgkb = Path(settings.pharmgkb_path) if settings.pharmgkb_path else ref_dir / "pharmgkb"

    return ReferenceBundle(
        genome_build=build,
        reference_dir=ref_dir,
        ref_fasta=ref_fasta,
        bwa_index_prefix=bwa_prefix,
        snpeff_db=settings.snpeff_db,
        dbsnp_vcf=dbsnp if dbsnp and dbsnp.exists() else None,
        clinvar_vcf=clinvar if clinvar.exists() else None,
        pharmgkb_dir=pharmgkb if pharmgkb.exists() else None,
    )


def sample_work_dir(sample_label: str) -> Path:
    settings = get_settings()
    return Path(settings.pipeline_work_dir) / sample_label

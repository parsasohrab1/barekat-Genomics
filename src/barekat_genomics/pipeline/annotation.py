"""حاشیه‌نویسی واریانت: SnpEff + یکپارچه‌سازی با پایگاه دانش ClinVar/PharmGKB."""

from __future__ import annotations

import csv
from pathlib import Path

from barekat_genomics.pipeline.exec import run_command, tool_available
from barekat_genomics.pipeline.reference import get_reference_bundle


def annotate_vcf(vcf_path: Path, work_dir: Path, genome_build: str) -> Path | None:
    """SnpEff annotation — در صورت نصب بودن."""
    if not tool_available("snpEff"):
        return _annotate_with_bcftools_cs(vcf_path, work_dir, genome_build)
    return _annotate_with_snpeff(vcf_path, work_dir, genome_build)


def _annotate_with_snpeff(vcf_path: Path, work_dir: Path, genome_build: str) -> Path:
    refs = get_reference_bundle(genome_build)
    out_vcf = work_dir / "annotated.vcf"
    run_command(
        [
            "snpEff", "ann",
            "-v", refs.snpeff_db,
            str(vcf_path),
            "-o", str(out_vcf),
        ],
        timeout=3600,
    )
    _enrich_with_clinvar_pharmgkb(out_vcf, work_dir, genome_build)
    return out_vcf


def _annotate_with_bcftools_cs(vcf_path: Path, work_dir: Path, genome_build: str) -> Path:
    """fallback: bcftools annotate با ClinVar در صورت موجود بودن."""
    refs = get_reference_bundle(genome_build)
    out_vcf = work_dir / "annotated.vcf.gz"
    cmd = ["bcftools", "view", str(vcf_path), "-Oz", "-o", str(out_vcf)]
    run_command(cmd, timeout=600)

    if refs.clinvar_vcf and refs.clinvar_vcf.is_file():
        clinvar_annotated = work_dir / "clinvar.annotated.vcf.gz"
        run_command(
            [
                "bcftools", "annotate",
                "-a", str(refs.clinvar_vcf),
                "-c", "INFO/CLNSIG,INFO/CLNREVSTAT",
                str(out_vcf),
                "-Oz", "-o", str(clinvar_annotated),
            ],
            timeout=1800,
        )
        out_vcf = clinvar_annotated

    run_command(["bcftools", "index", str(out_vcf)], timeout=300)
    return out_vcf


def _enrich_with_clinvar_pharmgkb(vcf_path: Path, work_dir: Path, genome_build: str) -> None:
    """افزودن اطلاعات PharmGKB از فایل CSV محلی."""
    refs = get_reference_bundle(genome_build)
    if not refs.pharmgkb_dir or not refs.pharmgkb_dir.is_dir():
        return

    pharmgkb_tsv = refs.pharmgkb_dir / "pharmgkb_variants.tsv"
    if not pharmgkb_tsv.is_file():
        return

    lookup: dict[str, str] = {}
    with open(pharmgkb_tsv, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rs = row.get("rsid") or row.get("RSID")
            drug = row.get("drug") or row.get("Drug")
            if rs and drug:
                lookup[rs] = drug

    if not lookup:
        return

    sidecar = work_dir / "pharmgkb_lookup.tsv"
    with open(sidecar, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["rsid", "drug"])
        for rs, drug in lookup.items():
            writer.writerow([rs, drug])

"""شناسایی واریانت: GATK HaplotypeCaller + پارس VCF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from barekat_genomics.pipeline.annotation import annotate_vcf
from barekat_genomics.pipeline.exec import ensure_dir, run_command
from barekat_genomics.pipeline.mode import is_production_pipeline
from barekat_genomics.pipeline.reference import get_reference_bundle


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
    gene: str | None = None
    consequence: str | None = None


from barekat_genomics.pipeline.pgx_genes import PHARMACOGENOMIC_GENES


def call_variants(
    file_path: str,
    file_type: str,
    genome_build: str = "GRCh38",
    work_dir: Path | None = None,
    bam_path: Path | None = None,
    assay_type: str = "panel",
) -> list[CalledVariant]:
    ft = file_type.upper()
    if ft == "VCF":
        # میان‌بر: فایل VCF آماده — فقط annotate/parse
        if is_production_pipeline():
            base_dir = ensure_dir(work_dir or Path(file_path).parent / "variants")
            annotated = annotate_vcf(Path(file_path), base_dir, genome_build)
            return parse_vcf(annotated if annotated else Path(file_path))
        return _run_simulated_calling()

    if is_production_pipeline():
        return _run_production_calling(
            file_path, ft, genome_build, work_dir, bam_path, assay_type=assay_type
        )
    return _run_simulated_calling()


def _run_simulated_calling() -> list[CalledVariant]:
    return [
        CalledVariant("chr1", 11796321, "G", "A", "SNP", 99.5, 45, "rs1801133"),
        CalledVariant("chr10", 96521657, "C", "T", "SNP", 98.2, 38, "rs4244285"),
        CalledVariant("chr19", 40991272, "C", "T", "SNP", 97.8, 42, "rs1799853"),
        CalledVariant("chr22", 42522613, "G", "A", "SNP", 96.5, 35, "rs1142345"),
        CalledVariant("chr1", 97915614, "C", "T", "SNP", 95.1, 30, "rs1800460"),
        CalledVariant("chr12", 21178615, "G", "A", "SNP", 94.3, 28, None),
        CalledVariant("chr6", 31356726, "T", "TC", "INDEL", 88.7, 22, None),
    ]


def _run_production_calling(
    file_path: str,
    file_type: str,
    genome_build: str,
    work_dir: Path | None,
    bam_path: Path | None,
    assay_type: str = "panel",
) -> list[CalledVariant]:
    from barekat_genomics.pipeline.assay_config import get_assay_profile, resolve_target_bed

    refs = get_reference_bundle(genome_build)
    if not refs.reference_ready:
        raise FileNotFoundError(f"مرجع ژنوم آماده نیست: {refs.ref_fasta}")

    base_dir = ensure_dir(work_dir or Path(file_path).parent / "variants")
    vcf_raw = base_dir / "raw.vcf.gz"

    bam = bam_path or Path(file_path)
    if file_type == "BAM":
        bam = Path(file_path)

    cmd = [
        "gatk", "HaplotypeCaller",
        "-R", str(refs.ref_fasta),
        "-I", str(bam),
        "-O", str(vcf_raw),
        "--native-pair-hmm-threads", "2",
    ]
    profile = get_assay_profile(assay_type)
    bed = resolve_target_bed(assay_type)
    if profile.haplotyper_intervals and bed is not None:
        cmd.extend(["-L", str(bed)])

    run_command(cmd, timeout=7200)

    annotated_vcf = annotate_vcf(vcf_raw, base_dir, genome_build)
    return parse_vcf(annotated_vcf if annotated_vcf else vcf_raw)


def parse_vcf(vcf_path: Path) -> list[CalledVariant]:
    """پارس VCF با bcftools query."""
    result = run_command(
        [
            "bcftools", "query",
            "-f", r"%CHROM\t%POS\t%REF\t%ALT\t%QUAL\t%INFO/DP\t%ID\t%ANN\n",
            str(vcf_path),
        ],
        timeout=600,
    )

    variants: list[CalledVariant] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        chrom, pos, ref, alt = parts[0], int(parts[1]), parts[2], parts[3]
        qual = float(parts[4]) if parts[4] != "." else 0.0
        depth = int(parts[5]) if len(parts) > 5 and parts[5] not in (".", "") else 0
        rs_id = parts[6] if len(parts) > 6 and parts[6] != "." else None

        gene, consequence = None, None
        if len(parts) > 7 and parts[7]:
            ann = parts[7].split("|")
            if len(ann) >= 4:
                consequence = ann[1] if ann[1] else None
                gene = ann[3] if ann[3] else None

        for single_alt in alt.split(","):
            vtype = "INDEL" if len(ref) != len(single_alt) else "SNP"
            variants.append(
                CalledVariant(
                    chromosome=chrom,
                    position=pos,
                    ref_allele=ref,
                    alt_allele=single_alt,
                    variant_type=vtype,
                    quality_score=qual,
                    depth=depth,
                    rs_id=rs_id,
                    gene=gene,
                    consequence=consequence,
                )
            )
    return variants


def filter_variants(
    variants: list[CalledVariant],
    min_quality: float = 30.0,
    min_depth: int = 10,
) -> list[CalledVariant]:
    return [v for v in variants if v.quality_score >= min_quality and v.depth >= min_depth]

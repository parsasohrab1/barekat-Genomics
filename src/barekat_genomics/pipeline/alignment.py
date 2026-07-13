"""هم‌ترازسازی BWA-MEM2 + samtools."""

from __future__ import annotations

from pathlib import Path

from barekat_genomics.pipeline.exec import ensure_dir, run_command
from barekat_genomics.pipeline.reference import get_reference_bundle


def align_fastq(
    fastq_path: str,
    work_dir: Path,
    genome_build: str = "GRCh38",
    read_group: str = "@RG\\tID:sample\\tSM:sample\\tPL:ILLUMINA",
) -> Path:
    """FASTQ → sorted BAM با BWA-MEM2 و samtools."""
    refs = get_reference_bundle(genome_build)
    if not refs.reference_ready:
        raise FileNotFoundError(
            f"مرجع ژنوم آماده نیست: {refs.ref_fasta}. "
            "راهنما: data/reference/README.md"
        )

    input_path = Path(fastq_path)
    align_dir = ensure_dir(work_dir / "alignment")
    sam_path = align_dir / f"{input_path.stem}.sam"
    bam_path = align_dir / f"{input_path.stem}.sorted.bam"

    run_command(
        [
            "bwa-mem2", "mem",
            "-R", read_group,
            str(refs.bwa_index_prefix),
            str(input_path),
            "-o", str(sam_path),
        ],
        timeout=7200,
    )

    run_command(
        ["samtools", "view", "-bS", str(sam_path), "-o", str(align_dir / "unsorted.bam")],
        timeout=1800,
    )
    run_command(
        [
            "samtools", "sort",
            str(align_dir / "unsorted.bam"),
            "-o", str(bam_path),
        ],
        timeout=1800,
    )
    run_command(["samtools", "index", str(bam_path)], timeout=600)

    return bam_path


def prepare_bam(bam_path: str, work_dir: Path) -> Path:
    """ایندکس BAM در صورت نیاز."""
    path = Path(bam_path)
    if not path.is_file():
        raise FileNotFoundError(f"BAM یافت نشد: {bam_path}")

    bai = path.with_suffix(path.suffix + ".bai")
    if not bai.is_file():
        run_command(["samtools", "index", str(path)], timeout=600)
    return path

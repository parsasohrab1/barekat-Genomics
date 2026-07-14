"""هم‌ترازسازی BWA-MEM2 + MarkDuplicates + samtools."""

from __future__ import annotations

from pathlib import Path

from barekat_genomics.pipeline.exec import ensure_dir, run_command, tool_available
from barekat_genomics.pipeline.reference import get_reference_bundle


def align_fastq(
    fastq_path: str,
    work_dir: Path,
    genome_build: str = "GRCh38",
    read_group: str = "@RG\\tID:sample\\tSM:sample\\tPL:ILLUMINA",
    fastq_r2: str | None = None,
) -> Path:
    """FASTQ → sorted BAM با BWA-MEM2، MarkDuplicates و samtools."""
    refs = get_reference_bundle(genome_build)
    if not refs.reference_ready:
        raise FileNotFoundError(
            f"مرجع ژنوم آماده نیست: {refs.ref_fasta}. "
            "راهنما: data/reference/README.md یا scripts/setup_reference.py"
        )

    input_path = Path(fastq_path)
    align_dir = ensure_dir(work_dir / "alignment")
    sam_path = align_dir / f"{input_path.stem}.sam"
    sorted_bam = align_dir / f"{input_path.stem}.sorted.bam"
    dedup_bam = align_dir / f"{input_path.stem}.dedup.bam"

    mem_cmd = [
        "bwa-mem2",
        "mem",
        "-R",
        read_group,
        str(refs.bwa_index_prefix),
        str(input_path),
    ]
    if fastq_r2:
        mem_cmd.append(str(fastq_r2))
    mem_cmd.extend(["-o", str(sam_path)])
    run_command(mem_cmd, timeout=7200)

    run_command(
        ["samtools", "view", "-bS", str(sam_path), "-o", str(align_dir / "unsorted.bam")],
        timeout=1800,
    )
    run_command(
        ["samtools", "sort", str(align_dir / "unsorted.bam"), "-o", str(sorted_bam)],
        timeout=1800,
    )
    run_command(["samtools", "index", str(sorted_bam)], timeout=600)

    # MarkDuplicates برای کاهش false positive در GATK
    if tool_available("gatk"):
        run_command(
            [
                "gatk",
                "MarkDuplicates",
                "-I",
                str(sorted_bam),
                "-O",
                str(dedup_bam),
                "-M",
                str(align_dir / "markduplicates_metrics.txt"),
                "--CREATE_INDEX",
                "true",
                "--VALIDATION_STRINGENCY",
                "SILENT",
            ],
            timeout=3600,
        )
        return dedup_bam

    return sorted_bam


def prepare_bam(bam_path: str, work_dir: Path) -> Path:
    """ایندکس BAM و در صورت امکان MarkDuplicates روی ورودی BAM."""
    path = Path(bam_path)
    if not path.is_file():
        raise FileNotFoundError(f"BAM یافت نشد: {bam_path}")

    align_dir = ensure_dir(work_dir / "alignment")
    bai = path.with_suffix(path.suffix + ".bai")
    if not bai.is_file() and not Path(str(path) + ".bai").is_file():
        run_command(["samtools", "index", str(path)], timeout=600)

    if tool_available("gatk"):
        dedup_bam = align_dir / f"{path.stem}.dedup.bam"
        run_command(
            [
                "gatk",
                "MarkDuplicates",
                "-I",
                str(path),
                "-O",
                str(dedup_bam),
                "-M",
                str(align_dir / "markduplicates_metrics.txt"),
                "--CREATE_INDEX",
                "true",
                "--VALIDATION_STRINGENCY",
                "SILENT",
            ],
            timeout=3600,
        )
        return dedup_bam

    return path

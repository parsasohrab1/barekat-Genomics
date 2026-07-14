"""مرحله پیش‌پردازش: FastQC + MultiQC / samtools QC + عمق پوشش."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from barekat_genomics.pipeline.exec import ensure_dir, run_command, tool_available
from barekat_genomics.pipeline.mode import is_production_pipeline


@dataclass
class QCMetrics:
    total_reads: int
    mean_quality: float
    gc_content: float
    duplication_rate: float
    passed: bool
    warnings: list[str]
    report_dir: str | None = None
    mean_depth: float | None = None
    coverage_pct_10x: float | None = None
    coverage_pct_20x: float | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k != "report_dir" or v is not None}


def run_quality_control(
    file_path: str,
    file_type: str,
    work_dir: Path | None = None,
) -> QCMetrics:
    if is_production_pipeline():
        return _run_production_qc(file_path, file_type, work_dir)
    return _run_simulated_qc(file_type)


def enrich_qc_with_bam_coverage(qc: QCMetrics, bam_path: Path) -> QCMetrics:
    """پس از alignment، متریک عمق پوشش را به QC اضافه می‌کند."""
    if not bam_path.is_file():
        return qc
    try:
        coverage = _compute_bam_coverage(bam_path)
    except Exception:
        return qc

    warnings = list(qc.warnings)
    if coverage["mean_depth"] is not None and coverage["mean_depth"] < 20:
        warnings.append("عمق میانگین پوشش کمتر از ۲۰×")
    if coverage["coverage_pct_20x"] is not None and coverage["coverage_pct_20x"] < 0.8:
        warnings.append("پوشش ۲۰× کمتر از ۸۰٪ بازه‌های هدف")

    passed = qc.passed and (coverage["mean_depth"] is None or coverage["mean_depth"] >= 10)

    return QCMetrics(
        total_reads=qc.total_reads,
        mean_quality=qc.mean_quality,
        gc_content=qc.gc_content,
        duplication_rate=qc.duplication_rate,
        passed=passed,
        warnings=warnings,
        report_dir=qc.report_dir,
        mean_depth=coverage["mean_depth"],
        coverage_pct_10x=coverage["coverage_pct_10x"],
        coverage_pct_20x=coverage["coverage_pct_20x"],
    )


def _run_simulated_qc(file_type: str) -> QCMetrics:
    warnings: list[str] = []
    if file_type == "FASTQ":
        total_reads, mean_quality, gc_content, duplication_rate = 1_000_000, 35.2, 0.42, 0.08
        mean_depth, cov10, cov20 = 48.5, 0.96, 0.91
    elif file_type == "BAM":
        total_reads, mean_quality, gc_content, duplication_rate = 950_000, 36.1, 0.41, 0.06
        mean_depth, cov10, cov20 = 52.0, 0.97, 0.93
    elif file_type in ("VCF", "CRAM"):
        total_reads, mean_quality, gc_content, duplication_rate = 0, 40.0, 0.42, 0.0
        mean_depth, cov10, cov20 = (80.0 if file_type == "CRAM" else 100.0), 0.99, 0.95
        warnings.append("ورودی VCF/CRAM — QC توالی خام محدود")
    else:
        raise ValueError(f"نوع فایل پشتیبانی‌نشده: {file_type}")

    if mean_quality < 20:
        warnings.append("کیفیت پایه پایین")
    if duplication_rate > 0.3:
        warnings.append("نرخ تکرار بالا")
    if gc_content < 0.35 or gc_content > 0.65:
        warnings.append("محتوای GC غیرعادی")

    return QCMetrics(
        total_reads=total_reads,
        mean_quality=mean_quality,
        gc_content=gc_content,
        duplication_rate=duplication_rate,
        passed=mean_quality >= 20 and duplication_rate <= 0.3,
        warnings=warnings,
        mean_depth=mean_depth,
        coverage_pct_10x=cov10,
        coverage_pct_20x=cov20,
    )


def _run_production_qc(file_path: str, file_type: str, work_dir: Path | None) -> QCMetrics:
    input_path = Path(file_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"فایل ورودی یافت نشد: {file_path}")

    qc_dir = ensure_dir((work_dir or input_path.parent) / "qc")
    warnings: list[str] = []

    if file_type == "FASTQ":
        run_command(["fastqc", "-o", str(qc_dir), "-t", "2", str(input_path)], timeout=3600)
        if tool_available("multiqc"):
            run_command(
                ["multiqc", str(qc_dir), "-o", str(qc_dir / "multiqc"), "--force"],
                timeout=600,
            )
        metrics = _parse_fastqc(qc_dir, input_path.stem)
    elif file_type == "BAM":
        flagstat = run_command(["samtools", "flagstat", str(input_path)], timeout=600)
        stats = run_command(["samtools", "stats", str(input_path)], timeout=600)
        metrics = _parse_samtools_qc(flagstat.stdout, stats.stdout)
        coverage = _compute_bam_coverage(input_path)
        metrics.update(coverage)
    else:
        raise ValueError(f"نوع فایل پشتیبانی‌نشده: {file_type}")

    if metrics["mean_quality"] < 20:
        warnings.append("کیفیت پایه پایین")
    if metrics["duplication_rate"] > 0.3:
        warnings.append("نرخ تکرار بالا")
    if metrics["gc_content"] < 0.35 or metrics["gc_content"] > 0.65:
        warnings.append("محتوای GC غیرعادی")

    multiqc_json = qc_dir / "multiqc" / "multiqc_data.json"
    if multiqc_json.is_file():
        with open(multiqc_json, encoding="utf-8") as f:
            mqc = json.load(f)
        warnings.extend(mqc.get("report_general_stats_data", [{}])[0].get("warnings", [])[:3])

    passed = metrics["mean_quality"] >= 20 and metrics["duplication_rate"] <= 0.3
    if metrics.get("mean_depth") is not None and metrics["mean_depth"] < 10:
        passed = False
        warnings.append("عمق میانگین پوشش کمتر از ۱۰×")

    return QCMetrics(
        total_reads=metrics["total_reads"],
        mean_quality=metrics["mean_quality"],
        gc_content=metrics["gc_content"],
        duplication_rate=metrics["duplication_rate"],
        passed=passed,
        warnings=warnings,
        report_dir=str(qc_dir),
        mean_depth=metrics.get("mean_depth"),
        coverage_pct_10x=metrics.get("coverage_pct_10x"),
        coverage_pct_20x=metrics.get("coverage_pct_20x"),
    )


def _compute_bam_coverage(bam_path: Path) -> dict:
    """محاسبه mean depth و درصد پوشش ۱۰×/۲۰× با sampling از samtools depth."""
    result = run_command(
        ["samtools", "depth", "-a", str(bam_path)],
        timeout=1800,
    )
    depths: list[int] = []
    ge10 = 0
    ge20 = 0
    # برای فایل‌های خیلی بزرگ فقط حداکثر ۱ میلیون پوزیشن را می‌خوانیم
    for i, line in enumerate(result.stdout.splitlines()):
        if i >= 1_000_000:
            break
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            d = int(parts[2])
        except ValueError:
            continue
        depths.append(d)
        if d >= 10:
            ge10 += 1
        if d >= 20:
            ge20 += 1

    if not depths:
        return {"mean_depth": None, "coverage_pct_10x": None, "coverage_pct_20x": None}

    n = len(depths)
    return {
        "mean_depth": round(sum(depths) / n, 2),
        "coverage_pct_10x": round(ge10 / n, 4),
        "coverage_pct_20x": round(ge20 / n, 4),
    }


def _parse_fastqc(qc_dir: Path, sample_stem: str) -> dict:
    fastqc_data = qc_dir / f"{sample_stem}_fastqc" / "fastqc_data.txt"
    if not fastqc_data.is_file():
        candidates = list(qc_dir.glob("*_fastqc/fastqc_data.txt"))
        fastqc_data = candidates[0] if candidates else fastqc_data

    total_reads = 0
    gc_content = 0.42
    mean_quality = 30.0
    duplication_rate = 0.08

    if fastqc_data.is_file():
        content = fastqc_data.read_text(encoding="utf-8", errors="ignore")
        m_reads = re.search(r"Total Sequences\s+(\d+)", content)
        if m_reads:
            total_reads = int(m_reads.group(1))
        m_gc = re.search(r"%GC\s+([\d.]+)", content)
        if m_gc:
            gc_content = float(m_gc.group(1)) / 100.0

        # % Duplicate Sequences from basic stats if present
        m_dup = re.search(r"#Total Deduplicated Percentage\s+([\d.]+)", content)
        if m_dup:
            # FastQC reports % remaining after dedup → duplication ≈ 100 - value
            remaining = float(m_dup.group(1))
            duplication_rate = max(0.0, min(1.0, (100.0 - remaining) / 100.0))

        qual_section = False
        qual_scores: list[float] = []
        for line in content.splitlines():
            if line.startswith(">>Per sequence quality scores"):
                qual_section = True
                continue
            if qual_section and line.startswith(">>"):
                break
            if qual_section and "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        score = float(parts[0])
                        count = float(parts[1])
                        qual_scores.extend([score] * int(min(count, 1000)))
                    except ValueError:
                        continue
        if qual_scores:
            mean_quality = sum(qual_scores) / len(qual_scores)

    return {
        "total_reads": total_reads or 1,
        "mean_quality": mean_quality,
        "gc_content": gc_content,
        "duplication_rate": duplication_rate,
    }


def _parse_samtools_qc(flagstat: str, stats: str) -> dict:
    total_reads = 0
    for line in flagstat.splitlines():
        if "in total" in line:
            total_reads = int(line.split()[0])
            break

    mean_quality = 30.0
    gc_content = 0.41
    duplication_rate = 0.06
    m_gc = re.search(r"GC percentage:\s+([\d.]+)", stats)
    if m_gc:
        gc_content = float(m_gc.group(1)) / 100.0
    m_mq = re.search(r"average quality:\s+([\d.]+)", stats)
    if m_mq:
        mean_quality = float(m_mq.group(1))
    m_dup = re.search(r"duplicates:\s+(\d+)", flagstat)
    if m_dup and total_reads > 0:
        duplication_rate = int(m_dup.group(1)) / total_reads

    return {
        "total_reads": total_reads or 1,
        "mean_quality": mean_quality,
        "gc_content": gc_content,
        "duplication_rate": duplication_rate,
    }

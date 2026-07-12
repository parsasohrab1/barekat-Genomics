"""مرحله پیش‌پردازش: کنترل کیفیت داده‌های توالی‌یابی."""

from dataclasses import dataclass


@dataclass
class QCMetrics:
    total_reads: int
    mean_quality: float
    gc_content: float
    duplication_rate: float
    passed: bool
    warnings: list[str]


def run_quality_control(file_path: str, file_type: str) -> QCMetrics:
    """
    اجرای کنترل کیفیت روی فایل FASTQ یا BAM.

    در محیط تولید، این تابع با ابزارهای واقعی (FastQC, samtools) یکپارچه می‌شود.
    """
    warnings: list[str] = []

    if file_type == "FASTQ":
        total_reads = 1_000_000
        mean_quality = 35.2
        gc_content = 0.42
        duplication_rate = 0.08
    elif file_type == "BAM":
        total_reads = 950_000
        mean_quality = 36.1
        gc_content = 0.41
        duplication_rate = 0.06
    else:
        raise ValueError(f"نوع فایل پشتیبانی‌نشده: {file_type}")

    if mean_quality < 20:
        warnings.append("کیفیت پایه پایین")
    if duplication_rate > 0.3:
        warnings.append("نرخ تکرار بالا")
    if gc_content < 0.35 or gc_content > 0.65:
        warnings.append("محتوای GC غیرعادی")

    passed = mean_quality >= 20 and duplication_rate <= 0.3

    return QCMetrics(
        total_reads=total_reads,
        mean_quality=mean_quality,
        gc_content=gc_content,
        duplication_rate=duplication_rate,
        passed=passed,
        warnings=warnings,
    )

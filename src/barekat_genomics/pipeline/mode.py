"""حالت اجرای پایپ‌لاین: simulated یا production."""

from barekat_genomics.core.config import get_settings
from barekat_genomics.pipeline.exec import tool_available


def is_production_pipeline() -> bool:
    settings = get_settings()
    if settings.pipeline_mode != "production":
        return False
    return all(tool_available(t) for t in ("fastqc", "bwa-mem2", "samtools", "gatk", "bcftools"))

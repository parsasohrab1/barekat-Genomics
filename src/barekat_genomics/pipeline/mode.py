"""حالت اجرای پایپ‌لاین: simulated یا production."""

from barekat_genomics.core.config import get_settings
from barekat_genomics.pipeline.exec import tool_available

REQUIRED_PRODUCTION_TOOLS = (
    "fastqc",
    "bwa-mem2",
    "samtools",
    "gatk",
    "bcftools",
    "snpEff",
)


def missing_production_tools() -> list[str]:
    return [t for t in REQUIRED_PRODUCTION_TOOLS if not tool_available(t)]


def is_production_pipeline() -> bool:
    settings = get_settings()
    if settings.pipeline_mode != "production":
        return False
    return len(missing_production_tools()) == 0


def assert_production_ready(genome_build: str | None = None) -> None:
    """بلاک شروع Job production در صورت نبود ابزار یا مرجع."""
    from barekat_genomics.pipeline.reference import validate_reference_bundle

    settings = get_settings()
    if settings.pipeline_mode != "production":
        return

    missing = missing_production_tools()
    if missing:
        raise RuntimeError(
            "حالت production فعال است ولی ابزارهای بیوانفورماتیک موجود نیستند: "
            + ", ".join(missing)
        )

    validation = validate_reference_bundle(genome_build)
    if not validation.ready:
        failed = validation.to_dict().get("failed") or [c.name for c in validation.checks if not c.ok]
        raise FileNotFoundError(
            f"مرجع ژنوم validation={validation.overall} "
            f"(failed={', '.join(failed)}). "
            "راهنما: data/reference/README.md یا scripts/setup_reference.py validate"
        )

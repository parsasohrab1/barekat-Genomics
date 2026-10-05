"""Pipeline execution mode: simulated or production."""

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
    """Block the start of a production Job if tools or the reference are missing."""
    from barekat_genomics.pipeline.reference import validate_reference_bundle

    settings = get_settings()
    if settings.pipeline_mode != "production":
        return

    missing = missing_production_tools()
    if missing:
        raise RuntimeError(
            "Production mode is enabled but bioinformatics tools are not available: "
            + ", ".join(missing)
        )

    validation = validate_reference_bundle(genome_build)
    if not validation.ready:
        failed = validation.to_dict().get("failed") or [c.name for c in validation.checks if not c.ok]
        raise FileNotFoundError(
            f"Genome reference validation={validation.overall} "
            f"(failed={', '.join(failed)}). "
            "Guide: data/reference/README.md or scripts/setup_reference.py validate"
        )

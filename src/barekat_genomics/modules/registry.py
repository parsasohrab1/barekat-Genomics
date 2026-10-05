"""Registry of incremental diagnostic modules."""

from __future__ import annotations

from dataclasses import dataclass

from barekat_genomics.modules.panels import (
    CARRIER_SCREENING_GENES,
    CGP_ACTIONABLE_GENES,
    CPIC_PANEL_GENES,
)


@dataclass(frozen=True)
class GenomicsModule:
    id: str
    name_fa: str
    name_en: str
    description_fa: str
    genes: frozenset[str]
    category: str
    requires_paired_sample: bool = False
    cpic_guideline: bool = False


MODULES: dict[str, GenomicsModule] = {
    "pharmacogenomics": GenomicsModule(
        id="pharmacogenomics",
        name_fa="Pharmacogenomics",
        name_en="Pharmacogenomics",
        description_fa="Analysis of variants related to drug response and CPIC recommendations",
        genes=CPIC_PANEL_GENES,
        category="pharmacogenomics",
        cpic_guideline=True,
    ),
    "pgx_panel": GenomicsModule(
        id="pgx_panel",
        name_fa="CPIC pharmacogenomic panel",
        name_en="CPIC Pharmacogenomics Panel",
        description_fa="Standard 18-gene CPIC panel with structured drug recommendations",
        genes=CPIC_PANEL_GENES,
        category="pharmacogenomics",
        cpic_guideline=True,
    ),
    "cgp": GenomicsModule(
        id="cgp",
        name_fa="Cancer genomic profile",
        name_en="Cancer Genomics Profiling",
        description_fa="Detection of actionable variants in cancer genes (hereditary + somatic)",
        genes=CGP_ACTIONABLE_GENES,
        category="oncology",
    ),
    "carrier_screening": GenomicsModule(
        id="carrier_screening",
        name_fa="Carrier screening",
        name_en="Carrier Screening",
        description_fa="Pre-pregnancy screening — identifying carriers of common genetic diseases",
        genes=CARRIER_SCREENING_GENES,
        category="reproductive",
    ),
    "tumor_normal": GenomicsModule(
        id="tumor_normal",
        name_fa="Tumor / normal",
        name_en="Tumor-Normal Comparison",
        description_fa="Comparison of tumor somatic variants against the normal sample",
        genes=CGP_ACTIONABLE_GENES,
        category="oncology",
        requires_paired_sample=True,
    ),
    "prs": GenomicsModule(
        id="prs",
        name_fa="Polygenic risk score",
        name_en="Polygenic Risk Score",
        description_fa="Risk assessment of common diseases based on SNP profile",
        genes=frozenset(),
        category="risk_prediction",
    ),
}

DEFAULT_MODULE = "pharmacogenomics"

_MODULE_ALIASES = {"pgx": "pharmacogenomics", "pgx_default": "pharmacogenomics"}


def get_module(module_id: str) -> GenomicsModule:
    resolved = _MODULE_ALIASES.get(module_id, module_id)
    mod = MODULES.get(resolved)
    if not mod:
        raise ValueError(f"Unknown module: {module_id}")
    return mod


def list_modules() -> list[GenomicsModule]:
    return list(MODULES.values())

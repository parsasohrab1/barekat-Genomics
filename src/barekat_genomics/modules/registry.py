"""ثبت ماژول‌های تشخیصی افزایشی."""

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
        name_fa="فارماکوژنومیک",
        name_en="Pharmacogenomics",
        description_fa="تحلیل واریانت‌های مرتبط با پاسخ دارویی و توصیه‌های CPIC",
        genes=CPIC_PANEL_GENES,
        category="pharmacogenomics",
        cpic_guideline=True,
    ),
    "pgx_panel": GenomicsModule(
        id="pgx_panel",
        name_fa="پنل فارماکوژنومیک CPIC",
        name_en="CPIC Pharmacogenomics Panel",
        description_fa="پنل استاندارد ۱۸ ژن CPIC با توصیه دارویی ساختاریافته",
        genes=CPIC_PANEL_GENES,
        category="pharmacogenomics",
        cpic_guideline=True,
    ),
    "cgp": GenomicsModule(
        id="cgp",
        name_fa="پروفایل ژنومی سرطان",
        name_en="Cancer Genomics Profiling",
        description_fa="تشخیص واریانت‌های actionable در ژن‌های سرطان (hereditary + somatic)",
        genes=CGP_ACTIONABLE_GENES,
        category="oncology",
    ),
    "carrier_screening": GenomicsModule(
        id="carrier_screening",
        name_fa="غربالگری ناقل",
        name_en="Carrier Screening",
        description_fa="غربالگری قبل از بارداری — شناسایی ناقلین بیماری‌های ژنتیکی شایع",
        genes=CARRIER_SCREENING_GENES,
        category="reproductive",
    ),
    "tumor_normal": GenomicsModule(
        id="tumor_normal",
        name_fa="تومور / نرمال",
        name_en="Tumor-Normal Comparison",
        description_fa="مقایسه واریانت‌های سوماتیک تومور در برابر نمونه نرمال",
        genes=CGP_ACTIONABLE_GENES,
        category="oncology",
        requires_paired_sample=True,
    ),
    "prs": GenomicsModule(
        id="prs",
        name_fa="امتیاز ریسک چندژنی",
        name_en="Polygenic Risk Score",
        description_fa="ارزیابی ریسک بیماری‌های شایع بر اساس پروفایل SNP",
        genes=frozenset(),
        category="risk_prediction",
    ),
}

DEFAULT_MODULE = "pharmacogenomics"


def get_module(module_id: str) -> GenomicsModule:
    mod = MODULES.get(module_id)
    if not mod:
        raise ValueError(f"ماژول ناشناخته: {module_id}")
    return mod


def list_modules() -> list[GenomicsModule]:
    return list(MODULES.values())

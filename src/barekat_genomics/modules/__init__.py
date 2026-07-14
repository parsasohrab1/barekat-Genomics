"""ماژول‌های تشخیصی افزایشی barekat Genomics."""

from barekat_genomics.modules.registry import GenomicsModule, get_module, list_modules

__all__ = [
    "GenomicsModule",
    "ModuleAnalysisResult",
    "analyze_module",
    "get_module",
    "list_modules",
    "result_to_dict",
]


def __getattr__(name: str):
    if name in {"ModuleAnalysisResult", "analyze_module", "result_to_dict"}:
        from barekat_genomics.modules import analyzer

        return getattr(analyzer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

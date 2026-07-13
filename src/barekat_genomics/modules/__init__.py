"""ماژول‌های تشخیصی افزایشی barekat Genomics."""

from barekat_genomics.modules.analyzer import ModuleAnalysisResult, analyze_module, result_to_dict
from barekat_genomics.modules.registry import GenomicsModule, get_module, list_modules

__all__ = [
    "GenomicsModule",
    "ModuleAnalysisResult",
    "analyze_module",
    "get_module",
    "list_modules",
    "result_to_dict",
]

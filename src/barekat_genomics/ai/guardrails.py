"""Safety controls — preventing direct diagnostic answers."""

from __future__ import annotations

import re

from barekat_genomics.ai.disclaimer import FULL_DISCLAIMER_FA

# Question patterns that need to be redirected to decision support
DIAGNOSIS_PATTERNS = [
    r"تشخیص",
    r"مبتلا\s*به",
    r"قطعا\s*دارد",
    r"حتما\s*بیمار",
    r"بیماری\s*دارد",
    r"should\s+i\s+diagnose",
    r"does\s+(the\s+)?patient\s+have",
    r"definitely\s+has",
    r"confirm\s+diagnosis",
]

_DIAG_RE = re.compile("|".join(DIAGNOSIS_PATTERNS), re.IGNORECASE)


def is_diagnosis_request(question: str) -> bool:
    return bool(_DIAG_RE.search(question.strip()))


def diagnosis_redirect_response() -> dict:
    return {
        "answer_fa": (
            "This system is not permitted to provide a direct disease diagnosis. "
            "I can provide the pharmacogenomic information of the variant from PharmGKB/CPIC "
            "to help your decision-making — for example effect on drug, evidence level, "
            "or CPIC recommendations. Please ask your question within this framework."
        ),
        "blocked": True,
        "disclaimer": FULL_DISCLAIMER_FA,
        "decision_support_only": True,
        "sources": [],
        "context_chunks": [],
    }


def wrap_answer(answer: str, *, blocked: bool = False) -> dict:
    return {
        "answer_fa": answer,
        "blocked": blocked,
        "disclaimer": FULL_DISCLAIMER_FA,
        "decision_support_only": True,
    }

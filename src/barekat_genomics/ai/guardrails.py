"""کنترل‌های ایمنی — جلوگیری از پاسخ‌های تشخیصی مستقیم."""

from __future__ import annotations

import re

from barekat_genomics.ai.disclaimer import FULL_DISCLAIMER_FA

# الگوهای پرسش که نیاز به هدایت به پشتیبان تصمیم دارند
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
            "این سامانه مجاز به ارائه تشخیص مستقیم بیماری نیست. "
            "می‌توانم اطلاعات فارماکوژنومیک واریانت را از PharmGKB/CPIC "
            "برای کمک به تصمیم‌گیری شما ارائه دهم — مثلاً اثر بر دارو، سطح شواهد، "
            "یا توصیه‌های CPIC. لطفاً سؤال خود را در این چارچوب بپرسید."
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

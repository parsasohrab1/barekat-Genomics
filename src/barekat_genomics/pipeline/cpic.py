"""راهنمای CPIC — بارگذاری از فایل رسمی cpic.tsv."""

from __future__ import annotations

from barekat_genomics.knowledge import get_knowledge_registry

CPIC_LEVEL_LABELS: dict[str, str] = {
    "A": "سطح A — شواهد قوی (توصیه قطعی)",
    "B": "سطح B — شواهد متوسط (توصیه ترجیحی)",
    "C": "سطح C — شواهد محدود (در صورت امکان جایگزین)",
    "D": "سطح D — بدون توصیه عملی",
}

# تداخلات دارویی (DrugBank / FDA label summaries)
DRUG_INTERACTIONS: list[dict] = [
    {
        "drugs": ("warfarin", "clopidogrel"),
        "severity": "major",
        "warning_fa": "خطر افزایش قابل توجه خونریزی گوارشی و داخل‌جمجمه‌ای",
        "recommendation_fa": "در صورت نیاز به ترکیب، پایش INR و علائم خونریزی ضروری است؛ ترکیب با احتیاط شدید.",
    },
    {
        "drugs": ("warfarin", "aspirin"),
        "severity": "major",
        "warning_fa": "افزایش خطر خونریزی به‌ویژه در سالمندان",
        "recommendation_fa": "حداقل دوز آسپرین و پایش منظم INR توصیه می‌شود.",
    },
    {
        "drugs": ("clopidogrel", "aspirin"),
        "severity": "moderate",
        "warning_fa": "دوگانه ضدپلاکتی — خطر خونریزی افزایش می‌یابد",
        "recommendation_fa": "در صورت تجویز DAPT، مدت کوتاه و ارزیابی ریسک-فایده انجام شود.",
    },
    {
        "drugs": ("azathioprine", "allopurinol"),
        "severity": "major",
        "warning_fa": "مهار متابولیسم آزاتیوپرین — خطر میلوساپرسیون شدید",
        "recommendation_fa": "از ترکیب خودداری شود یا دوز آزاتیوپرین به ۲۵٪ کاهش یابد.",
    },
    {
        "drugs": ("fluorouracil", "capecitabine"),
        "severity": "major",
        "warning_fa": "مسیر متابولیکی مشترک DPYD — سمیت تجمعی",
        "recommendation_fa": "هرگز به‌صورت همزمان تجویز نشود.",
    },
    {
        "drugs": ("warfarin", "fluorouracil"),
        "severity": "moderate",
        "warning_fa": "فلوروراسیل مهار متابولیسم وارفارین را افزایش می‌دهد",
        "recommendation_fa": "پایش INR با فواصل کوتاه‌تر در طول شیمی‌درمانی.",
    },
]

SEVERITY_LABELS: dict[str, str] = {
    "major": "شدید",
    "moderate": "متوسط",
    "minor": "خفیف",
}


def _drug_fa(drug: str) -> str:
    registry = get_knowledge_registry()
    for (_, d), info in registry.cpic_guidelines().items():
        if d == drug.lower():
            return info.get("drug_fa") or drug
    return drug


def get_cpic_info(drug: str, gene: str | None = None) -> dict:
    registry = get_knowledge_registry()
    if gene:
        info = registry.get_cpic_for_gene_drug(gene, drug)
        if info:
            return {
                "drug_fa": info.get("drug_fa", drug),
                "gene": info.get("gene", gene),
                "cpic_level": info.get("cpic_level", "C"),
                "guideline": info.get("guideline"),
                "action_fa": info.get("action_fa"),
            }
    for (g, d), info in registry.cpic_guidelines().items():
        if d == drug.lower():
            return {
                "drug_fa": info.get("drug_fa", drug),
                "gene": info.get("gene", g),
                "cpic_level": info.get("cpic_level", "C"),
                "guideline": info.get("guideline"),
                "action_fa": info.get("action_fa"),
            }
    return {
        "drug_fa": drug,
        "gene": gene or "—",
        "cpic_level": "C",
        "guideline": "CPIC — شواهد محدود",
        "action_fa": "پایش بالینی و ارزیابی موردی توصیه می‌شود.",
    }


def detect_drug_interactions(recommended_drugs: list[str]) -> list[dict]:
    drug_set = {d.lower() for d in recommended_drugs}
    found = []
    for interaction in DRUG_INTERACTIONS:
        a, b = interaction["drugs"]
        if a in drug_set and b in drug_set:
            found.append(
                {
                    "drugs": [a, b],
                    "drugs_fa": [_drug_fa(a), _drug_fa(b)],
                    "severity": interaction["severity"],
                    "severity_label": SEVERITY_LABELS.get(interaction["severity"], interaction["severity"]),
                    "warning_fa": interaction["warning_fa"],
                    "recommendation_fa": interaction["recommendation_fa"],
                }
            )
    return found

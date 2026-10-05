"""CPIC guideline — loaded from the official cpic.tsv file."""

from __future__ import annotations

from barekat_genomics.knowledge import get_knowledge_registry

CPIC_LEVEL_LABELS: dict[str, str] = {
    "A": "Level A — strong evidence (definitive recommendation)",
    "B": "Level B — moderate evidence (preferred recommendation)",
    "C": "Level C — limited evidence (alternative if possible)",
    "D": "Level D — no actionable recommendation",
}

# Drug interactions (DrugBank / FDA label summaries)
DRUG_INTERACTIONS: list[dict] = [
    {
        "drugs": ("warfarin", "clopidogrel"),
        "severity": "major",
        "warning_fa": "Significantly increased risk of gastrointestinal and intracranial bleeding",
        "recommendation_fa": "If combination is needed, INR and bleeding signs must be monitored; combine with extreme caution.",
    },
    {
        "drugs": ("warfarin", "aspirin"),
        "severity": "major",
        "warning_fa": "Increased bleeding risk, especially in the elderly",
        "recommendation_fa": "The minimum aspirin dose and regular INR monitoring are recommended.",
    },
    {
        "drugs": ("clopidogrel", "aspirin"),
        "severity": "moderate",
        "warning_fa": "Dual antiplatelet therapy — bleeding risk increases",
        "recommendation_fa": "If DAPT is prescribed, use a short duration and perform a risk-benefit assessment.",
    },
    {
        "drugs": ("azathioprine", "allopurinol"),
        "severity": "major",
        "warning_fa": "Inhibition of azathioprine metabolism — risk of severe myelosuppression",
        "recommendation_fa": "Avoid the combination or reduce the azathioprine dose to 25%.",
    },
    {
        "drugs": ("fluorouracil", "capecitabine"),
        "severity": "major",
        "warning_fa": "Shared DPYD metabolic pathway — cumulative toxicity",
        "recommendation_fa": "Never prescribe concurrently.",
    },
    {
        "drugs": ("warfarin", "fluorouracil"),
        "severity": "moderate",
        "warning_fa": "Fluorouracil increases inhibition of warfarin metabolism",
        "recommendation_fa": "Monitor INR at shorter intervals during chemotherapy.",
    },
]

SEVERITY_LABELS: dict[str, str] = {
    "major": "Severe",
    "moderate": "Moderate",
    "minor": "Mild",
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
        "guideline": "CPIC — limited evidence",
        "action_fa": "Clinical monitoring and case-by-case evaluation are recommended.",
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

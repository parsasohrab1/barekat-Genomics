"""RAG سبک روی PharmGKB/CPIC — بازیابی + پاسخ مبتنی بر دانش."""

from __future__ import annotations

import re

from barekat_genomics.ai.guardrails import is_diagnosis_request, wrap_answer
from barekat_genomics.knowledge.models import VariantKnowledge
from barekat_genomics.knowledge.registry import KnowledgeRegistry, get_knowledge_registry
from barekat_genomics.pipeline.variant_calling import CalledVariant

RSID_RE = re.compile(r"\brs\d+\b", re.IGNORECASE)

KNOWN_GENES = {
    "CYP2D6", "CYP2C19", "CYP2C9", "CYP3A5", "TPMT", "DPYD", "SLCO1B1",
    "VKORC1", "UGT1A1", "HLA-B", "HLA-A", "G6PD", "MTHFR", "BRCA1", "BRCA2",
    "CFTR", "CHEK2", "TP53",
}

KNOWN_DRUGS = {
    "warfarin", "clopidogrel", "codeine", "tamoxifen", "fluorouracil",
    "azathioprine", "mercaptopurine", "simvastatin", "methotrexate",
    "وارفارین", "کلوپیدوگرل", "فلوروراسیل", "آزاتیوپرین",
}


def _kb_to_chunk(rsid: str, kb: VariantKnowledge) -> str:
    parts = [f"[{', '.join(kb.sources) or 'Knowledge'}]"]
    if rsid:
        parts.append(rsid)
    if kb.gene:
        parts.append(f"ژن {kb.gene}")
    if kb.drug:
        parts.append(f"دارو {kb.drug}")
    if kb.phenotype:
        parts.append(kb.phenotype)
    if kb.pgx_level:
        parts.append(f"سطح PharmGKB: {kb.pgx_level}")
    if kb.cpic_level:
        parts.append(f"سطح CPIC: {kb.cpic_level}")
    if kb.cpic_action_fa:
        parts.append(f"توصیه CPIC: {kb.cpic_action_fa}")
    if kb.clinical_significance:
        parts.append(f"ClinVar: {kb.clinical_significance}")
    if kb.gnomad_af is not None:
        parts.append(f"فراوانی gnomAD: {kb.gnomad_af:.4f}")
    return " — ".join(parts)


def _extract_entities(question: str) -> dict:
    rsids = [r.lower() for r in RSID_RE.findall(question)]
    upper_q = question.upper()
    genes = [g for g in KNOWN_GENES if g in upper_q]
    lower_q = question.lower()
    drugs = [d for d in KNOWN_DRUGS if d in lower_q]
    return {"rsids": rsids, "genes": genes, "drugs": drugs}


def retrieve_context(
    question: str,
    *,
    variant: CalledVariant | None = None,
    annotation: dict | None = None,
    registry: KnowledgeRegistry | None = None,
) -> tuple[list[str], list[str]]:
    """بازیابی قطعات دانش مرتبط."""
    reg = registry or get_knowledge_registry()
    reg._ensure_loaded()

    chunks: list[str] = []
    sources: list[str] = []
    seen_rsids: set[str] = set()

    entities = _extract_entities(question)

    if variant:
        kb = reg.lookup(variant)
        if kb:
            rs = variant.rs_id or "?"
            chunks.append(_kb_to_chunk(rs, kb))
            sources.extend(kb.sources)
            if variant.rs_id:
                seen_rsids.add(variant.rs_id.lower())

    if annotation:
        ann_text = (
            f"[گزارش بالینی] ژن {annotation.get('gene')} — "
            f"{annotation.get('interpretation', '')} — "
            f"اهمیت: {annotation.get('clinical_significance')}"
        )
        chunks.append(ann_text)

    for rsid in entities["rsids"]:
        if rsid in seen_rsids:
            continue
        kb = reg._by_rsid.get(rsid)  # noqa: SLF001 — intentional for RAG retrieval
        if kb:
            chunks.append(_kb_to_chunk(rsid, kb))
            sources.extend(kb.sources)
            seen_rsids.add(rsid)

    for gene in entities["genes"]:
        for rsid, kb in reg._by_rsid.items():  # noqa: SLF001
            if kb.gene and kb.gene.upper() == gene and rsid not in seen_rsids:
                chunks.append(_kb_to_chunk(rsid, kb))
                sources.extend(kb.sources)
                seen_rsids.add(rsid)
                if len(chunks) >= 8:
                    break

    for drug in entities["drugs"]:
        drug_l = drug.lower()
        for rsid, kb in reg._by_rsid.items():  # noqa: SLF001
            if kb.drug and drug_l in kb.drug.lower() and rsid not in seen_rsids:
                chunks.append(_kb_to_chunk(rsid, kb))
                sources.extend(kb.sources)
                seen_rsids.add(rsid)

    return chunks[:10], sorted(set(sources))


def compose_answer(question: str, chunks: list[str], sources: list[str]) -> dict:
    """ساخت پاسخ فارسی از قطعات بازیابی‌شده (بدون LLM)."""
    if not chunks:
        answer = (
            "در پایگاه دانش PharmGKB/CPIC موجود، اطلاعات مستقیمی برای این سؤال یافت نشد. "
            "لطفاً rsID، نام ژن، یا دارو را مشخص کنید."
        )
        result = wrap_answer(answer)
        result["sources"] = []
        result["context_chunks"] = []
        return result

    intro = "بر اساس منابع PharmGKB و CPIC موجود در سامانه:\n\n"
    body_parts = []
    for i, chunk in enumerate(chunks, 1):
        body_parts.append(f"{i}. {chunk}")

    closing = (
        "\n\nاین اطلاعات صرفاً برای پشتیبانی تصمیم بالینی است و "
        "جایگزین قضاوت پزشک یا تشخیص قطعی نیست."
    )
    answer = intro + "\n".join(body_parts) + closing

    result = wrap_answer(answer)
    result["sources"] = sources
    result["context_chunks"] = chunks
    result["question"] = question
    return result


def answer_variant_question(
    question: str,
    *,
    variant: CalledVariant | None = None,
    annotation: dict | None = None,
    registry: KnowledgeRegistry | None = None,
) -> dict:
    if is_diagnosis_request(question):
        from barekat_genomics.ai.guardrails import diagnosis_redirect_response

        return diagnosis_redirect_response()

    chunks, sources = retrieve_context(
        question,
        variant=variant,
        annotation=annotation,
        registry=registry,
    )
    return compose_answer(question, chunks, sources)

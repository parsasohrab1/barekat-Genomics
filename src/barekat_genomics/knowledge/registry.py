"""رجیستری یکپارچه پایگاه دانش — جستجو بر اساس rsID یا موقعیت."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from barekat_genomics.core.config import get_settings
from barekat_genomics.knowledge.loaders import (
    load_clinvar_tsv,
    load_cpic_tsv,
    load_dbsnp_tsv,
    load_gnomad_tsv,
    load_pharmgkb_tsv,
)
from barekat_genomics.knowledge.models import VariantKnowledge

if TYPE_CHECKING:
    from barekat_genomics.pipeline.variant_calling import CalledVariant


def _default_knowledge_dir() -> Path:
    settings = get_settings()
    if settings.knowledge_dir:
        return Path(settings.knowledge_dir)
    return Path(__file__).resolve().parents[3] / "data" / "reference" / "knowledge"


class KnowledgeRegistry:
    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self.knowledge_dir = knowledge_dir or _default_knowledge_dir()
        self._loaded = False
        self._by_rsid: dict[str, VariantKnowledge] = {}
        self._by_pos: dict[str, VariantKnowledge] = {}
        self._cpic_gene_drug: dict[tuple[str, str], dict] = {}

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        d = self.knowledge_dir

        for rsid, rec in load_dbsnp_tsv(d / "dbsnp.tsv").items():
            self._merge_rsid(rsid, rec)
        for rsid, rec in load_pharmgkb_tsv(d / "pharmgkb.tsv").items():
            self._merge_rsid(rsid, rec)

        clinvar = load_clinvar_tsv(d / "clinvar.tsv")
        for key, rec in clinvar.items():
            if key.startswith("chr"):
                self._merge_pos(key, rec)
            else:
                self._merge_rsid(key, rec)

        gnomad = load_gnomad_tsv(d / "gnomad.tsv")
        for key, rec in gnomad.items():
            if key.startswith("chr"):
                self._merge_pos(key, rec)
            else:
                self._merge_rsid(key, rec)

        cpic_by_gene, self._cpic_gene_drug = load_cpic_tsv(d / "cpic.tsv")
        self._merge_variant_scores(d / "variant_scores.tsv")
        for rsid, rec in list(self._by_rsid.items()):
            if rec.gene and rec.gene.upper() in cpic_by_gene:
                self._merge_rsid(rsid, cpic_by_gene[rec.gene.upper()])

        self._loaded = True

    def _merge_rsid(self, rsid: str, rec: VariantKnowledge) -> None:
        existing = self._by_rsid.get(rsid)
        self._by_rsid[rsid] = existing.merge(rec) if existing else rec
        if rec.chromosome and rec.position:
            self._merge_pos(f"{rec.chromosome}:{rec.position}", rec)

    def _merge_pos(self, key: str, rec: VariantKnowledge) -> None:
        existing = self._by_pos.get(key)
        self._by_pos[key] = existing.merge(rec) if existing else rec

    def _merge_variant_scores(self, path: Path) -> None:
        from barekat_genomics.ml.dataset import load_variant_scores

        for rsid, sc in load_variant_scores(path).items():
            rec = VariantKnowledge(
                rs_id=rsid,
                cadd_phred=sc.get("cadd_phred"),
                sift_score=sc.get("sift_score"),
                polyphen_score=sc.get("polyphen_score"),
                phylop_score=sc.get("phylop_score"),
                sources=["CADD/SIFT/PolyPhen"],
            )
            self._merge_rsid(rsid, rec)

    def lookup(self, variant: CalledVariant) -> VariantKnowledge | None:
        self._ensure_loaded()
        result: VariantKnowledge | None = None

        if variant.rs_id:
            rs = variant.rs_id if variant.rs_id.startswith("rs") else f"rs{variant.rs_id}"
            result = self._by_rsid.get(rs)

        chrom = variant.chromosome if variant.chromosome.startswith("chr") else f"chr{variant.chromosome}"
        pos_rec = self._by_pos.get(f"{chrom}:{variant.position}")
        if pos_rec:
            result = result.merge(pos_rec) if result else pos_rec

        if result and result.gene and result.drug:
            cpic = self._cpic_gene_drug.get((result.gene.upper(), result.drug.lower()))
            if cpic:
                result = result.merge(
                    VariantKnowledge(
                        cpic_level=cpic.get("cpic_level"),
                        cpic_guideline=cpic.get("guideline"),
                        cpic_action_fa=cpic.get("action_fa"),
                        drug_fa=cpic.get("drug_fa"),
                        sources=["CPIC"],
                    )
                )

        return result

    def get_cpic_for_gene_drug(self, gene: str, drug: str) -> dict | None:
        self._ensure_loaded()
        return self._cpic_gene_drug.get((gene.upper(), drug.lower()))

    def drug_for_gene(self, gene: str | None) -> str | None:
        self._ensure_loaded()
        if not gene:
            return None
        for rec in self._by_rsid.values():
            if rec.gene and rec.gene.upper() == gene.upper() and rec.drug:
                return rec.drug
        return None

    def cpic_guidelines(self) -> dict[tuple[str, str], dict]:
        self._ensure_loaded()
        return dict(self._cpic_gene_drug)


@lru_cache
def get_knowledge_registry() -> KnowledgeRegistry:
    return KnowledgeRegistry()

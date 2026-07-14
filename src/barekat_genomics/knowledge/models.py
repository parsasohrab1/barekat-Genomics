"""مدل‌های یکپارچه پایگاه دانش."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VariantKnowledge:
    rs_id: str | None = None
    chromosome: str | None = None
    position: int | None = None
    ref_allele: str | None = None
    alt_allele: str | None = None
    gene: str | None = None
    consequence: str | None = None
    # PharmGKB
    drug: str | None = None
    drugs: list[str] = field(default_factory=list)
    phenotype: str | None = None
    pgx_level: str | None = None
    # CPIC
    cpic_level: str | None = None
    cpic_guideline: str | None = None
    cpic_action_fa: str | None = None
    drug_fa: str | None = None
    # ClinVar
    clinical_significance: str | None = None
    clinvar_review_status: str | None = None
    # gnomAD
    gnomad_af: float | None = None
    # درون‌گنی (CADD, SIFT, PolyPhen, conservation)
    cadd_phred: float | None = None
    sift_score: float | None = None
    polyphen_score: float | None = None
    phylop_score: float | None = None
    # provenance
    sources: list[str] = field(default_factory=list)

    def merge(self, other: VariantKnowledge) -> VariantKnowledge:
        """ادغام رکوردها با اولویت مقادیر غیرخالی."""
        for src in other.sources:
            if src not in self.sources:
                self.sources.append(src)
        for drug in other.drugs:
            if drug and drug not in self.drugs:
                self.drugs.append(drug)
        if other.drug and other.drug not in self.drugs:
            self.drugs.append(other.drug)
        if self.drug is None and other.drug is not None:
            self.drug = other.drug
        if not self.drugs and self.drug:
            self.drugs = [self.drug]
        for attr in (
            "rs_id", "chromosome", "position", "ref_allele", "alt_allele",
            "gene", "consequence", "phenotype", "pgx_level",
            "cpic_level", "cpic_guideline", "cpic_action_fa", "drug_fa",
            "clinical_significance", "clinvar_review_status", "gnomad_af",
            "cadd_phred", "sift_score", "polyphen_score", "phylop_score",
        ):
            if getattr(self, attr) is None and getattr(other, attr) is not None:
                setattr(self, attr, getattr(other, attr))
        return self

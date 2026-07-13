"""بارگذاری فایل‌های TSV/VCF صادرشده از منابع رسمی."""

from __future__ import annotations

import csv
from pathlib import Path

from barekat_genomics.knowledge.models import VariantKnowledge

CLINVAR_SIG_MAP = {
    "pathogenic": "pathogenic",
    "likely pathogenic": "likely_pathogenic",
    "likely_pathogenic": "likely_pathogenic",
    "uncertain significance": "uncertain_significance",
    "uncertain_significance": "uncertain_significance",
    "benign": "benign",
    "likely benign": "benign",
    "likely_benign": "benign",
    "drug_response": "pathogenic",
}


def _norm_rsid(rsid: str | None) -> str | None:
    if not rsid:
        return None
    rs = rsid.strip()
    if not rs or rs == ".":
        return None
    return rs if rs.startswith("rs") else f"rs{rs}"


def _norm_chrom(chrom: str | None) -> str | None:
    if not chrom:
        return None
    c = chrom.strip()
    if c.startswith("chr"):
        return c
    return f"chr{c}"


def load_dbsnp_tsv(path: Path) -> dict[str, VariantKnowledge]:
    """dbSNP: rsid, chrom, pos, ref, alt"""
    by_rsid: dict[str, VariantKnowledge] = {}
    if not path.is_file():
        return by_rsid

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rsid = _norm_rsid(row.get("rsid") or row.get("RSID") or row.get("rs"))
            if not rsid:
                continue
            rec = VariantKnowledge(
                rs_id=rsid,
                chromosome=_norm_chrom(row.get("chrom") or row.get("CHROM")),
                position=int(row["pos"]) if row.get("pos") else None,
                ref_allele=row.get("ref") or row.get("REF"),
                alt_allele=row.get("alt") or row.get("ALT"),
                sources=["dbSNP"],
            )
            by_rsid[rsid] = rec
    return by_rsid


def load_pharmgkb_tsv(path: Path) -> dict[str, VariantKnowledge]:
    """
    PharmGKB clinical annotations export:
    rsid, gene, drug, phenotype, pgx_level
    """
    by_rsid: dict[str, VariantKnowledge] = {}
    if not path.is_file():
        return by_rsid

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rsid = _norm_rsid(
                row.get("rsid") or row.get("RSID") or row.get("Variant/Haplotypes")
            )
            if not rsid:
                continue
            rec = VariantKnowledge(
                rs_id=rsid,
                gene=row.get("gene") or row.get("Gene"),
                drug=(row.get("drug") or row.get("Drug(s)") or row.get("Drug") or "").lower() or None,
                phenotype=row.get("phenotype") or row.get("Phenotype(s)") or row.get("Phenotype"),
                pgx_level=row.get("pgx_level") or row.get("PGx Level"),
                sources=["PharmGKB"],
            )
            existing = by_rsid.get(rsid)
            by_rsid[rsid] = existing.merge(rec) if existing else rec
    return by_rsid


def load_cpic_tsv(path: Path) -> tuple[dict[str, VariantKnowledge], dict[tuple[str, str], dict]]:
    """
    CPIC gene-drug pairs:
    gene, drug, cpic_level, guideline, action_fa, drug_fa

    Returns (by_gene index for rsid merge via gene, gene_drug lookup table)
    """
    by_gene: dict[str, VariantKnowledge] = {}
    gene_drug: dict[tuple[str, str], dict] = {}
    if not path.is_file():
        return by_gene, gene_drug

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            gene = (row.get("gene") or row.get("Gene") or "").strip().upper()
            drug = (row.get("drug") or row.get("Drug") or "").strip().lower()
            if not gene or not drug:
                continue
            info = {
                "gene": gene,
                "drug": drug,
                "drug_fa": row.get("drug_fa") or row.get("Drug_FA"),
                "cpic_level": row.get("cpic_level") or row.get("CPIC_Level") or "C",
                "guideline": row.get("guideline") or row.get("Guideline"),
                "action_fa": row.get("action_fa") or row.get("Recommendation"),
            }
            gene_drug[(gene, drug)] = info
            rec = VariantKnowledge(
                gene=gene,
                drug=drug,
                drug_fa=info.get("drug_fa"),
                cpic_level=info.get("cpic_level"),
                cpic_guideline=info.get("guideline"),
                cpic_action_fa=info.get("action_fa"),
                sources=["CPIC"],
            )
            existing = by_gene.get(gene)
            by_gene[gene] = existing.merge(rec) if existing else rec
    return by_gene, gene_drug


def load_clinvar_tsv(path: Path) -> dict[str, VariantKnowledge]:
    """ClinVar summary: rsid, chrom, pos, clinical_significance, review_status"""
    by_rsid: dict[str, VariantKnowledge] = {}
    by_pos: dict[str, VariantKnowledge] = {}
    if not path.is_file():
        return by_rsid

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            raw_sig = (row.get("clinical_significance") or row.get("ClinicalSignificance") or "").lower()
            sig = CLINVAR_SIG_MAP.get(raw_sig.replace("_", " "), raw_sig.replace(" ", "_") or None)
            rec = VariantKnowledge(
                rs_id=_norm_rsid(row.get("rsid") or row.get("RSID")),
                chromosome=_norm_chrom(row.get("chrom") or row.get("Chromosome")),
                position=int(row["pos"]) if row.get("pos") else None,
                clinical_significance=sig,
                clinvar_review_status=row.get("review_status") or row.get("ReviewStatus"),
                sources=["ClinVar"],
            )
            if rec.rs_id:
                existing = by_rsid.get(rec.rs_id)
                by_rsid[rec.rs_id] = existing.merge(rec) if existing else rec
            elif rec.chromosome and rec.position:
                key = f"{rec.chromosome}:{rec.position}"
                existing = by_pos.get(key)
                by_pos[key] = existing.merge(rec) if existing else rec

    by_rsid.update(by_pos)
    return by_rsid


def load_gnomad_tsv(path: Path) -> dict[str, VariantKnowledge]:
    """gnomAD frequencies: rsid, chrom, pos, ref, alt, af"""
    by_rsid: dict[str, VariantKnowledge] = {}
    by_pos: dict[str, VariantKnowledge] = {}
    if not path.is_file():
        return by_rsid

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            af_raw = row.get("af") or row.get("AF") or row.get("af_exome") or row.get("AF_exome")
            try:
                af = float(af_raw) if af_raw not in (None, "", ".") else None
            except ValueError:
                af = None
            rec = VariantKnowledge(
                rs_id=_norm_rsid(row.get("rsid") or row.get("RSID")),
                chromosome=_norm_chrom(row.get("chrom") or row.get("CHROM")),
                position=int(row["pos"]) if row.get("pos") else None,
                ref_allele=row.get("ref") or row.get("REF"),
                alt_allele=row.get("alt") or row.get("ALT"),
                gnomad_af=af,
                sources=["gnomAD"],
            )
            if rec.rs_id:
                existing = by_rsid.get(rec.rs_id)
                by_rsid[rec.rs_id] = existing.merge(rec) if existing else rec
            elif rec.chromosome and rec.position:
                key = f"{rec.chromosome}:{rec.position}"
                existing = by_pos.get(key)
                by_pos[key] = existing.merge(rec) if existing else rec

    by_rsid.update(by_pos)
    return by_rsid

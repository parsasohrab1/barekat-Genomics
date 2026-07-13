"""ساخت دیتاست برچسب‌خورده از ClinVar + PharmGKB."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from barekat_genomics.knowledge.loaders import CLINVAR_SIG_MAP, load_clinvar_tsv, load_pharmgkb_tsv, load_gnomad_tsv
from barekat_genomics.knowledge.models import VariantKnowledge
from barekat_genomics.ml.features import FEATURE_NAMES, extract_features
from barekat_genomics.pipeline.variant_calling import CalledVariant

POSITIVE_SIGS = {"pathogenic", "likely_pathogenic", "drug_response", "risk_factor"}
NEGATIVE_SIGS = {"benign", "likely_benign"}


def _label_from_clinvar(sig: str | None) -> int | None:
    if not sig:
        return None
    normalized = CLINVAR_SIG_MAP.get(sig.lower().replace(" ", "_"), sig.lower())
    if normalized in POSITIVE_SIGS or sig.lower() == "drug_response":
        return 1
    if normalized in NEGATIVE_SIGS:
        return 0
    return None


def load_variant_scores(path: Path) -> dict[str, dict]:
    """CADD, SIFT, PolyPhen, PhyloP از فایل annotation."""
    scores: dict[str, dict] = {}
    if not path.is_file():
        return scores
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rsid = row.get("rsid") or row.get("RSID")
            if not rsid:
                continue
            rs = rsid if rsid.startswith("rs") else f"rs{rsid}"
            scores[rs] = {
                "cadd_phred": float(row["cadd"]) if row.get("cadd") else None,
                "sift_score": float(row["sift"]) if row.get("sift") else None,
                "polyphen_score": float(row["polyphen"]) if row.get("polyphen") else None,
                "phylop_score": float(row["phylop"]) if row.get("phylop") else None,
            }
    return scores


def build_labeled_dataset(knowledge_dir: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    برچسب‌گذاری:
    - مثبت: ClinVar pathogenic/drug_response یا PharmGKB level 1A/1B
    - منفی: ClinVar benign
    """
    d = knowledge_dir
    clinvar = load_clinvar_tsv(d / "clinvar.tsv")
    pharmgkb = load_pharmgkb_tsv(d / "pharmgkb.tsv")
    gnomad = load_gnomad_tsv(d / "gnomad.tsv")
    scores = load_variant_scores(d / "variant_scores.tsv")

    X_rows: list[list[float]] = []
    y_rows: list[int] = []
    ids: list[str] = []

    all_rsids = set(clinvar.keys()) | set(pharmgkb.keys()) | set(scores.keys())
    for rsid in sorted(all_rsids):
        if rsid.startswith("chr"):
            continue

        cv = clinvar.get(rsid, VariantKnowledge())
        pg = pharmgkb.get(rsid, VariantKnowledge())
        gm = gnomad.get(rsid, VariantKnowledge())
        sc = scores.get(rsid, {})

        kb = VariantKnowledge().merge(cv).merge(pg).merge(gm)
        if sc.get("cadd_phred") is not None:
            kb.cadd_phred = sc["cadd_phred"]
        if sc.get("sift_score") is not None:
            kb.sift_score = sc["sift_score"]
        if sc.get("polyphen_score") is not None:
            kb.polyphen_score = sc["polyphen_score"]
        if sc.get("phylop_score") is not None:
            kb.phylop_score = sc["phylop_score"]

        label = _label_from_clinvar(cv.clinical_significance)
        if label is None and kb.pgx_level:
            label = 1 if kb.pgx_level.strip().upper() in ("1A", "1B", "A") else 0
        if label is None:
            continue

        variant = CalledVariant(
            chromosome=kb.chromosome or "chr1",
            position=kb.position or 0,
            ref_allele=kb.ref_allele or "N",
            alt_allele=kb.alt_allele or "N",
            variant_type="SNP",
            quality_score=95.0,
            depth=40,
            rs_id=rsid,
            gene=kb.gene,
        )
        fv = extract_features(variant, kb.gene, kb)
        X_rows.append(fv.to_list())
        y_rows.append(label)
        ids.append(rsid)

    if not X_rows:
        raise ValueError(f"هیچ نمونه برچسب‌خورده‌ای در {knowledge_dir} یافت نشد")

    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int32), ids


def augment_dataset(
    X: np.ndarray,
    y: np.ndarray,
    *,
    noise: float = 0.03,
    copies: int = 20,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """افزایش داده با نویز کنترل‌شده برای آموزش پایدار."""
    rng = np.random.RandomState(seed)
    xs, ys = [X], [y]
    for _ in range(copies):
        noisy = X + rng.normal(0, noise, size=X.shape)
        noisy = np.clip(noisy, 0.0, 1.0)
        xs.append(noisy.astype(np.float32))
        ys.append(y.copy())
    return np.vstack(xs), np.concatenate(ys)

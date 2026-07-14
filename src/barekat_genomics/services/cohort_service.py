"""تحلیل کوهورت و discovery نشانگر برای جمعیت ایرانی."""

from __future__ import annotations

import csv
import math
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy.orm import Session

from barekat_genomics.models.cohort import Cohort, CohortMember
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.variant import Variant, VariantAnnotation


def _iranian_af_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "reference" / "knowledge" / "iranian_af.tsv"


def load_iranian_af(path: Path | None = None) -> dict[str, dict]:
    """بارگذاری فراوانی الل جمعیت ایرانی (rsid → AF)."""
    p = path or _iranian_af_path()
    out: dict[str, dict] = {}
    if not p.is_file():
        return out
    with open(p, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rsid = (row.get("rsid") or row.get("rs_id") or "").strip()
            if not rsid:
                continue
            try:
                af = float(row.get("af") or row.get("AF") or 0)
            except ValueError:
                af = 0.0
            out[rsid] = {
                "af": af,
                "gene": row.get("gene"),
                "n_chrom": int(row.get("n_chrom") or row.get("an") or 0) or None,
                "source": row.get("source") or "iranian_reference",
            }
    return out


class CohortService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        code: str,
        name: str,
        name_fa: str | None = None,
        population: str = "iranian",
        description: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> Cohort:
        existing = self.db.query(Cohort).filter(Cohort.code == code).first()
        if existing:
            raise ValueError(f"کوهورت تکراری: {code}")
        cohort = Cohort(
            code=code,
            name=name,
            name_fa=name_fa,
            population=population,
            description=description,
            organization_id=organization_id,
            status="active",
        )
        self.db.add(cohort)
        self.db.commit()
        self.db.refresh(cohort)
        return cohort

    def list(
        self, organization_id: uuid.UUID | None = None, population: str | None = None
    ) -> list[Cohort]:
        q = self.db.query(Cohort)
        if organization_id is not None:
            q = q.filter(Cohort.organization_id == organization_id)
        if population:
            q = q.filter(Cohort.population == population)
        return q.order_by(Cohort.created_at.desc()).all()

    def get(self, cohort_id: uuid.UUID) -> Cohort | None:
        return self.db.query(Cohort).filter(Cohort.id == cohort_id).first()

    def add_sample(self, cohort_id: uuid.UUID, sample_id: uuid.UUID) -> CohortMember:
        sample = self.db.query(SequencingSample).filter(SequencingSample.id == sample_id).first()
        if not sample:
            raise ValueError("نمونه یافت نشد")
        existing = (
            self.db.query(CohortMember)
            .filter(CohortMember.cohort_id == cohort_id, CohortMember.sample_id == sample_id)
            .first()
        )
        if existing:
            return existing
        patient = self.db.query(Patient).filter(Patient.id == sample.patient_id).first()
        m = CohortMember(
            cohort_id=cohort_id,
            sample_id=sample_id,
            patient_external_id=patient.external_id if patient else None,
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def discover_biomarkers(self, cohort_id: uuid.UUID, *, top_k: int = 20) -> dict:
        """
        اولویت‌بندی نشانگر در کوهورت:
        - فراوانی حامل در کوهورت
        - غنی‌سازی نسبت به AF ایرانی (enrichment)
        - سهم واریانت‌های با اهمیت بالینی بالا
        """
        cohort = self.get(cohort_id)
        if not cohort:
            raise ValueError("کوهورت یافت نشد")

        members = self.db.query(CohortMember).filter(CohortMember.cohort_id == cohort_id).all()
        sample_ids = [m.sample_id for m in members]
        n_samples = len(sample_ids)
        if n_samples == 0:
            return {
                "cohort_id": str(cohort_id),
                "population": cohort.population,
                "n_samples": 0,
                "markers": [],
            }

        rows = (
            self.db.query(Variant, VariantAnnotation)
            .outerjoin(VariantAnnotation, VariantAnnotation.variant_id == Variant.id)
            .filter(Variant.sample_id.in_(sample_ids))
            .all()
        )

        iranian = load_iranian_af()
        by_rsid: dict[str, dict] = defaultdict(
            lambda: {
                "samples": set(),
                "genes": Counter(),
                "sig": Counter(),
                "priority_sum": 0.0,
                "count": 0,
            }
        )

        for variant, ann in rows:
            key = variant.rs_id or f"{variant.chromosome}:{variant.position}"
            bucket = by_rsid[key]
            bucket["samples"].add(str(variant.sample_id))
            bucket["count"] += 1
            if ann and ann.gene:
                bucket["genes"][ann.gene] += 1
            if ann and ann.clinical_significance:
                bucket["sig"][ann.clinical_significance] += 1
            if ann and ann.priority_score:
                bucket["priority_sum"] += float(ann.priority_score)

        markers = []
        for rsid, info in by_rsid.items():
            carrier_n = len(info["samples"])
            carrier_af = carrier_n / n_samples
            ref = iranian.get(rsid) if rsid.startswith("rs") else None
            pop_af = float(ref["af"]) if ref else None
            # enrichment: نسبت فراوانی کوهورت به جمعیت مرجع (با هموارسازی)
            if pop_af is not None and pop_af > 0:
                enrichment = carrier_af / max(pop_af, 1e-6)
            else:
                enrichment = carrier_af * 10.0  # نشانگر بدون مرجع AF ایرانی
            pathogenic_share = 0.0
            total_sig = sum(info["sig"].values()) or 1
            pathogenic_share = (
                info["sig"].get("pathogenic", 0) + info["sig"].get("likely_pathogenic", 0)
            ) / total_sig
            score = (
                0.45 * min(math.log2(1 + enrichment), 5) / 5
                + 0.35 * pathogenic_share
                + 0.20 * min(info["priority_sum"] / max(info["count"], 1), 1.0)
            )
            gene = info["genes"].most_common(1)[0][0] if info["genes"] else None
            markers.append(
                {
                    "rs_id": rsid if rsid.startswith("rs") else None,
                    "locus": None if rsid.startswith("rs") else rsid,
                    "gene": gene or (ref.get("gene") if ref else None),
                    "carrier_count": carrier_n,
                    "cohort_af": round(carrier_af, 4),
                    "iranian_af": round(pop_af, 4) if pop_af is not None else None,
                    "enrichment": round(enrichment, 3),
                    "discovery_score": round(score, 4),
                    "pathogenic_share": round(pathogenic_share, 3),
                    "iranian_source": ref.get("source") if ref else None,
                }
            )

        markers.sort(key=lambda m: m["discovery_score"], reverse=True)
        return {
            "cohort_id": str(cohort_id),
            "cohort_code": cohort.code,
            "population": cohort.population,
            "n_samples": n_samples,
            "n_variant_observations": len(rows),
            "iranian_af_loaded": len(iranian),
            "markers": markers[:top_k],
        }

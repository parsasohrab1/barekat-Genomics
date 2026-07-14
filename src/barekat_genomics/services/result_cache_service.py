"""کش نتایج پایپ‌لاین و برآورد هزینه محاسبات."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from barekat_genomics.models.result_cache import ComputeCostRecord, PipelineResultCache
from barekat_genomics.pipeline.assay_config import get_assay_profile


def content_hash_for_path(path: str | Path, *, max_bytes: int = 1_048_576) -> str:
    """هش محتوای فایل (تا 1MB اول + اندازه) برای کلید کش."""
    p = Path(path)
    h = hashlib.sha256()
    h.update(str(p.name).encode())
    if p.is_file():
        size = p.stat().st_size
        h.update(str(size).encode())
        with open(p, "rb") as f:
            h.update(f.read(max_bytes))
    else:
        h.update(str(path).encode())
    return h.hexdigest()


def build_pipeline_cache_key(
    *,
    content_hash: str,
    file_type: str,
    assay_type: str,
    genome_build: str,
    module_id: str,
) -> str:
    raw = f"{content_hash}|{file_type}|{assay_type}|{genome_build}|{module_id}"
    return "pipe:" + hashlib.sha256(raw.encode()).hexdigest()[:40]


class ResultCacheService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, cache_key: str) -> dict | None:
        row = (
            self.db.query(PipelineResultCache)
            .filter(PipelineResultCache.cache_key == cache_key)
            .first()
        )
        if not row or not row.result_json:
            return None
        row.hit_count = (row.hit_count or 0) + 1
        row.last_hit_at = datetime.now(timezone.utc)
        self.db.commit()
        return dict(row.result_json)

    def put(
        self,
        *,
        cache_key: str,
        content_hash: str,
        file_type: str,
        assay_type: str,
        genome_build: str,
        module_id: str,
        result: dict,
    ) -> PipelineResultCache:
        existing = (
            self.db.query(PipelineResultCache)
            .filter(PipelineResultCache.cache_key == cache_key)
            .first()
        )
        payload = json.loads(json.dumps(result, default=str))
        if existing:
            existing.result_json = payload
            existing.content_hash = content_hash
            self.db.commit()
            self.db.refresh(existing)
            return existing
        row = PipelineResultCache(
            cache_key=cache_key,
            assay_type=assay_type,
            file_type=file_type,
            content_hash=content_hash,
            genome_build=genome_build,
            module_id=module_id,
            result_json=payload,
            hit_count=0,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def stats(self) -> dict:
        total = self.db.query(PipelineResultCache).count()
        hits = self.db.query(PipelineResultCache).filter(PipelineResultCache.hit_count > 0).count()
        return {"entries": total, "entries_with_hits": hits}


class ComputeCostService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def estimate(self, assay_type: str, *, cache_hit: bool = False) -> dict:
        profile = get_assay_profile(assay_type)
        factor = 0.05 if cache_hit else 1.0
        return {
            "assay_type": profile.assay_type,
            "estimated_cpu_hours": round(profile.estimated_cpu_hours * factor, 3),
            "estimated_usd": round(profile.estimated_usd * factor, 4),
            "cache_hit": cache_hit,
        }

    def record(
        self,
        *,
        organization_id: uuid.UUID | None,
        job_id: uuid.UUID | None,
        assay_type: str,
        backend: str,
        cache_hit: bool,
        notes: str | None = None,
    ) -> ComputeCostRecord:
        est = self.estimate(assay_type, cache_hit=cache_hit)
        row = ComputeCostRecord(
            organization_id=organization_id,
            job_id=job_id,
            assay_type=assay_type,
            backend=backend,
            cpu_seconds=est["estimated_cpu_hours"] * 3600,
            estimated_usd=est["estimated_usd"],
            cache_hit=cache_hit,
            notes=notes,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def summary(self, organization_id: uuid.UUID | None = None) -> dict:
        q = self.db.query(ComputeCostRecord)
        if organization_id is not None:
            q = q.filter(ComputeCostRecord.organization_id == organization_id)
        rows = q.all()
        total_usd = sum(r.estimated_usd or 0 for r in rows)
        cache_hits = sum(1 for r in rows if r.cache_hit)
        return {
            "jobs": len(rows),
            "cache_hits": cache_hits,
            "total_estimated_usd": round(total_usd, 4),
            "avg_usd": round(total_usd / len(rows), 4) if rows else 0.0,
        }

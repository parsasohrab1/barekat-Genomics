"""کش Redis + PostgreSQL برای تفسیر واریانت."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import redis
from sqlalchemy.orm import Session

from barekat_genomics.core.config import get_settings
from barekat_genomics.core.database import SessionLocal
from barekat_genomics.models.annotation_cache import AnnotationCacheEntry
from barekat_genomics.pipeline.variant_calling import CalledVariant

logger = logging.getLogger(__name__)

PRIORITY_URGENT = "urgent"
PRIORITY_NORMAL = "normal"
CELERY_QUEUE_URGENT = "urgent"
CELERY_QUEUE_DEFAULT = "default"


def build_cache_key(
    variant: CalledVariant,
    *,
    genome_build: str = "GRCh38",
    model_version: str = "v1",
) -> str:
    if variant.rs_id:
        return f"ann:{genome_build}:{model_version}:{variant.rs_id}"
    return (
        f"ann:{genome_build}:{model_version}:"
        f"{variant.chromosome}:{variant.position}:{variant.ref_allele}:{variant.alt_allele}"
    )


class AnnotationCacheService:
    """دو لایه Redis (سریع) + PostgreSQL (پایدار)."""

    def __init__(self, db: Session | None = None) -> None:
        self.settings = get_settings()
        self._db = db
        self._redis: redis.Redis | None = None

    @property
    def enabled(self) -> bool:
        return self.settings.annotation_cache_enabled

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    def _db_session(self) -> Session:
        return self._db if self._db is not None else SessionLocal()

    def get(
        self,
        variant: CalledVariant,
        *,
        genome_build: str = "GRCh38",
        model_version: str = "v1",
    ) -> dict | None:
        if not self.enabled:
            return None

        key = build_cache_key(variant, genome_build=genome_build, model_version=model_version)

        try:
            raw = self._get_redis().get(key)
            if raw:
                self._get_redis().expire(key, self.settings.annotation_cache_ttl_seconds)
                return json.loads(raw)
        except redis.RedisError as exc:
            logger.warning("annotation_cache_redis_miss", extra={"error": str(exc)})

        own_session = self._db is None
        db = self._db_session()
        try:
            row = db.query(AnnotationCacheEntry).filter(AnnotationCacheEntry.cache_key == key).first()
            if not row:
                return None
            row.hit_count += 1
            row.last_hit_at = datetime.now(timezone.utc)
            db.commit()
            try:
                self._get_redis().setex(
                    key,
                    self.settings.annotation_cache_ttl_seconds,
                    json.dumps(row.annotation_data),
                )
            except redis.RedisError:
                pass
            return row.annotation_data
        finally:
            if own_session:
                db.close()

    def set(
        self,
        variant: CalledVariant,
        annotation_data: dict,
        *,
        genome_build: str = "GRCh38",
        model_version: str = "v1",
    ) -> None:
        if not self.enabled:
            return

        key = build_cache_key(variant, genome_build=genome_build, model_version=model_version)

        try:
            self._get_redis().setex(
                key, self.settings.annotation_cache_ttl_seconds, json.dumps(annotation_data)
            )
        except redis.RedisError as exc:
            logger.warning("annotation_cache_redis_set_failed", extra={"error": str(exc)})

        own_session = self._db is None
        db = self._db_session()
        try:
            row = db.query(AnnotationCacheEntry).filter(AnnotationCacheEntry.cache_key == key).first()
            if row:
                row.annotation_data = annotation_data
                row.model_version = model_version
            else:
                db.add(
                    AnnotationCacheEntry(
                        cache_key=key,
                        rs_id=variant.rs_id,
                        genome_build=genome_build,
                        model_version=model_version,
                        annotation_data=annotation_data,
                    )
                )
            db.commit()
        finally:
            if own_session:
                db.close()

    def stats(self) -> dict:
        own_session = self._db is None
        db = self._db_session()
        try:
            total = db.query(AnnotationCacheEntry).count()
            return {"enabled": self.enabled, "db_entries": total}
        finally:
            if own_session:
                db.close()

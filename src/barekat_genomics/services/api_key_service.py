"""سرویس کلید API شرکا."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from barekat_genomics.models.api_key import PartnerApiKey


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ApiKeyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        scopes: str = "samples:write,pipeline:run,reports:read,cohorts:read",
        rate_limit_per_minute: int = 60,
    ) -> tuple[PartnerApiKey, str]:
        raw = f"bk_live_{secrets.token_urlsafe(32)}"
        prefix = raw[:12]
        row = PartnerApiKey(
            organization_id=organization_id,
            name=name,
            key_prefix=prefix,
            key_hash=_hash_key(raw),
            scopes=scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row, raw

    def list_for_org(self, organization_id: uuid.UUID) -> list[PartnerApiKey]:
        return (
            self.db.query(PartnerApiKey)
            .filter(PartnerApiKey.organization_id == organization_id)
            .order_by(PartnerApiKey.created_at.desc())
            .all()
        )

    def revoke(self, key_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        row = (
            self.db.query(PartnerApiKey)
            .filter(
                PartnerApiKey.id == key_id,
                PartnerApiKey.organization_id == organization_id,
            )
            .first()
        )
        if not row:
            return False
        row.is_active = False
        self.db.commit()
        return True

    def authenticate(self, raw_key: str) -> PartnerApiKey | None:
        if not raw_key:
            return None
        digest = _hash_key(raw_key)
        row = (
            self.db.query(PartnerApiKey)
            .filter(PartnerApiKey.key_hash == digest, PartnerApiKey.is_active.is_(True))
            .first()
        )
        if row:
            row.last_used_at = datetime.now(timezone.utc)
            self.db.commit()
        return row

    def has_scope(self, key: PartnerApiKey, scope: str) -> bool:
        scopes = {s.strip() for s in (key.scopes or "").split(",") if s.strip()}
        return scope in scopes or "*" in scopes

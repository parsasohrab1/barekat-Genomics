"""مدیریت کلید API شرکا + آمار هزینه/کش."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.services.api_key_service import ApiKeyService
from barekat_genomics.services.organization_service import OrganizationService
from barekat_genomics.services.result_cache_service import ComputeCostService, ResultCacheService

router = APIRouter(prefix="/integrations")


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: str = "samples:write,pipeline:run,reports:read,cohorts:read"
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: str
    rate_limit_per_minute: int
    is_active: bool

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    api_key: str


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_keys(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PARTNER_KEYS_MANAGE)),
) -> list[ApiKeyResponse]:
    org_id = user.organization_id or OrganizationService(db).ensure_default().id
    return [ApiKeyResponse.model_validate(k) for k in ApiKeyService(db).list_for_org(org_id)]


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PARTNER_KEYS_MANAGE)),
) -> ApiKeyCreatedResponse:
    org_id = user.organization_id or OrganizationService(db).ensure_default().id
    row, raw = ApiKeyService(db).create(
        organization_id=org_id,
        name=body.name,
        scopes=body.scopes,
        rate_limit_per_minute=body.rate_limit_per_minute,
    )
    return ApiKeyCreatedResponse(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        scopes=row.scopes,
        rate_limit_per_minute=row.rate_limit_per_minute,
        is_active=row.is_active,
        api_key=raw,
    )


@router.delete("/api-keys/{key_id}")
def revoke_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.PARTNER_KEYS_MANAGE)),
) -> dict:
    org_id = user.organization_id or OrganizationService(db).ensure_default().id
    ok = ApiKeyService(db).revoke(key_id, org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="کلید یافت نشد")
    return {"revoked": True}


@router.get("/compute/summary")
def compute_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.COMPUTE_READ)),
) -> dict:
    cost = ComputeCostService(db).summary(user.organization_id)
    cache = ResultCacheService(db).stats()
    return {"cost": cost, "pipeline_cache": cache}

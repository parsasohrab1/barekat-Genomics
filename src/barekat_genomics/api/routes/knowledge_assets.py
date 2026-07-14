"""ثبت دارایی دانشی / مالکیت فکری."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.services.knowledge_asset_service import (
    ASSET_TYPES,
    DISCLOSURE_STATUSES,
    KnowledgeAssetService,
)

router = APIRouter(prefix="/knowledge-assets")


class AssetCreate(BaseModel):
    asset_code: str
    title: str
    title_fa: str | None = None
    asset_type: str = Field(pattern="^(model|method|software_kit|dataset|guideline)$")
    version: str = "1.0"
    inventors: str | None = None
    disclosure_status: str = Field(default="internal", pattern="^(internal|disclosed|filed|granted|licensed)$")
    patent_ref: str | None = None
    license: str | None = None
    description: str | None = None
    linked_artifact: str | None = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    asset_code: str
    title: str
    title_fa: str | None = None
    asset_type: str
    version: str
    inventors: str | None = None
    disclosure_status: str
    patent_ref: str | None = None
    license: str | None = None
    description: str | None = None
    linked_artifact: str | None = None

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    disclosure_status: str
    patent_ref: str | None = None


@router.get("/", response_model=list[AssetResponse])
def list_assets(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.KNOWLEDGE_ASSETS_READ)),
) -> list[AssetResponse]:
    rows = KnowledgeAssetService(db).list(organization_id=user.organization_id)
    return [AssetResponse.model_validate(r) for r in rows]


@router.post("/", response_model=AssetResponse, status_code=201)
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.KNOWLEDGE_ASSETS_MANAGE)),
) -> AssetResponse:
    try:
        asset = KnowledgeAssetService(db).create(
            organization_id=user.organization_id,
            **body.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AssetResponse.model_validate(asset)


@router.patch("/{asset_id}/status", response_model=AssetResponse)
def update_status(
    asset_id: uuid.UUID,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.KNOWLEDGE_ASSETS_MANAGE)),
) -> AssetResponse:
    try:
        asset = KnowledgeAssetService(db).update_status(
            asset_id, body.disclosure_status, patent_ref=body.patent_ref
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not asset:
        raise HTTPException(status_code=404, detail="دارایی یافت نشد")
    return AssetResponse.model_validate(asset)


@router.get("/meta/enums")
def enums(_: CurrentUser = Depends(require_permission(Permission.KNOWLEDGE_ASSETS_READ))) -> dict:
    return {"asset_types": list(ASSET_TYPES), "disclosure_statuses": list(DISCLOSURE_STATUSES)}

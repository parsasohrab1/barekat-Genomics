"""API کوهورت و discovery نشانگر."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, get_current_user, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.services.cohort_service import CohortService, load_iranian_af

router = APIRouter(prefix="/cohorts")


class CohortCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100)
    name: str
    name_fa: str | None = None
    population: str = "iranian"
    description: str | None = None


class CohortResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    name_fa: str | None = None
    population: str
    status: str
    description: str | None = None

    model_config = {"from_attributes": True}


class AddMemberRequest(BaseModel):
    sample_id: uuid.UUID


@router.get("/", response_model=list[CohortResponse])
def list_cohorts(
    population: str | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.COHORTS_READ)),
) -> list[CohortResponse]:
    rows = CohortService(db).list(organization_id=user.organization_id, population=population)
    return [CohortResponse.model_validate(r) for r in rows]


@router.post("/", response_model=CohortResponse, status_code=201)
def create_cohort(
    body: CohortCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.COHORTS_WRITE)),
) -> CohortResponse:
    try:
        cohort = CohortService(db).create(
            code=body.code,
            name=body.name,
            name_fa=body.name_fa,
            population=body.population,
            description=body.description,
            organization_id=user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CohortResponse.model_validate(cohort)


@router.post("/{cohort_id}/members", status_code=201)
def add_member(
    cohort_id: uuid.UUID,
    body: AddMemberRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.COHORTS_WRITE)),
) -> dict:
    try:
        m = CohortService(db).add_sample(cohort_id, body.sample_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(m.id), "sample_id": str(m.sample_id)}


@router.get("/{cohort_id}/discovery")
def discover(
    cohort_id: uuid.UUID,
    top_k: int = 20,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.COHORTS_READ)),
) -> dict:
    try:
        return CohortService(db).discover_biomarkers(cohort_id, top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/meta/iranian-af")
def iranian_af_meta(
    _: CurrentUser = Depends(require_permission(Permission.COHORTS_READ)),
) -> dict:
    data = load_iranian_af()
    return {"n_markers": len(data), "sample_rsids": list(data.keys())[:20]}

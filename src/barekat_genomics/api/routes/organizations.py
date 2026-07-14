"""سازمان‌ها (multi-tenant)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, get_current_user, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations")


class OrganizationCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str
    name_fa: str | None = None
    deployment_mode: str = Field(default="saas", pattern="^(saas|on_prem)$")


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    name_fa: str | None = None
    deployment_mode: str
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.TENANT_MANAGE)),
) -> list[OrganizationResponse]:
    orgs = OrganizationService(db).list_all()
    if user.role != "admin":
        orgs = [o for o in orgs if o.id == user.organization_id]
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.get("/me", response_model=OrganizationResponse)
def my_organization(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> OrganizationResponse:
    svc = OrganizationService(db)
    if user.organization_id:
        org = svc.get(user.organization_id)
    else:
        org = svc.ensure_default()
    if not org:
        raise HTTPException(status_code=404, detail="سازمان یافت نشد")
    return OrganizationResponse.model_validate(org)


@router.post("/", response_model=OrganizationResponse, status_code=201)
def create_organization(
    body: OrganizationCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.TENANT_MANAGE)),
) -> OrganizationResponse:
    svc = OrganizationService(db)
    if svc.get_by_slug(body.slug):
        raise HTTPException(status_code=400, detail="slug تکراری است")
    org = svc.create(
        slug=body.slug,
        name=body.name,
        name_fa=body.name_fa,
        deployment_mode=body.deployment_mode,
    )
    svc.add_member(org.id, user.id, org_role="owner")
    return OrganizationResponse.model_validate(org)

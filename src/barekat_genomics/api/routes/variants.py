"""Variant listing endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, get_current_user
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission, has_permission, is_privileged_role
from barekat_genomics.knowledge import get_knowledge_registry
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.pipeline.variant_calling import CalledVariant
from barekat_genomics.schemas import VariantAnnotationResponse, VariantListItem

router = APIRouter(prefix="/variants")
_registry = get_knowledge_registry()


@router.get("/", response_model=list[VariantListItem])
def list_variants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[VariantListItem]:
    if not (
        has_permission(user.role, Permission.VARIANTS_READ)
        or has_permission(user.role, Permission.VARIANTS_READ_OWN)
    ):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="دسترسی مجاز نیست")

    query = (
        db.query(Variant, SequencingSample, Patient)
        .join(SequencingSample, Variant.sample_id == SequencingSample.id)
        .join(Patient, SequencingSample.patient_id == Patient.id)
        .order_by(Variant.created_at.desc())
    )
    if not is_privileged_role(user.role):
        query = query.filter(Patient.assigned_clinician_id == user.id)

    rows = query.offset(skip).limit(limit).all()

    result = []
    for variant, _sample, patient in rows:
        annotations = (
            db.query(VariantAnnotation)
            .filter(VariantAnnotation.variant_id == variant.id)
            .all()
        )
        ann_responses = [VariantAnnotationResponse.model_validate(a) for a in annotations]
        primary = annotations[0] if annotations else None
        kb = _registry.lookup(
            CalledVariant(
                chromosome=variant.chromosome,
                position=variant.position,
                ref_allele=variant.ref_allele,
                alt_allele=variant.alt_allele,
                variant_type=variant.variant_type,
                quality_score=variant.quality_score or 0.0,
                depth=variant.depth or 0,
                rs_id=variant.rs_id,
                gene=primary.gene if primary else None,
            )
        )
        result.append(
            VariantListItem(
                id=variant.id,
                chromosome=variant.chromosome,
                position=variant.position,
                ref_allele=variant.ref_allele,
                alt_allele=variant.alt_allele,
                variant_type=variant.variant_type,
                quality_score=variant.quality_score,
                rs_id=variant.rs_id,
                annotations=ann_responses,
                patient_external_id=patient.external_id,
                drug=kb.drug if kb else _registry.drug_for_gene(primary.gene if primary else None),
            )
        )
    return result

"""Genomic report endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import (
    CurrentUser,
    assert_patient_access,
    get_current_user,
    require_permission,
)
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission, Role, has_permission
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.variant import Variant
from barekat_genomics.schemas import (
    PendingVariantItem,
    ReportApproveRequest,
    ReportResponse,
    ReviewQueueItem,
    VariantResponse,
    VariantReviewRequest,
    VariantWithAnnotation,
)
from barekat_genomics.services.patient_service import PatientService
from barekat_genomics.services.report_service import ReportService
from barekat_genomics.services.review_service import ReviewService

router = APIRouter(prefix="/reports")


def _can_read_reports(user: CurrentUser) -> bool:
    return has_permission(user.role, Permission.REPORTS_READ) or has_permission(
        user.role, Permission.REPORTS_READ_OWN
    )


@router.get("/", response_model=list[ReportResponse])
def list_reports(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[ReportResponse]:
    if not _can_read_reports(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    service = ReportService(db)
    reports = service.list_for_user(user.id, user.role, skip=skip, limit=limit)
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/patient/{patient_id}", response_model=list[ReportResponse])
def list_patient_reports(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[ReportResponse]:
    if not _can_read_reports(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    patient = PatientService(db).get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)
    service = ReportService(db)
    reports = service.list_by_patient(patient_id, role=user.role)
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/review-queue", response_model=list[ReviewQueueItem])
def list_review_queue(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.VARIANTS_INTERPRET)),
) -> list[ReviewQueueItem]:
    review = ReviewService(db)
    reports = review.list_review_queue(skip=skip, limit=limit)
    items = []
    for report in reports:
        item = ReviewQueueItem.model_validate(report)
        item.pending_variant_count = review.pending_variant_count(report.id)
        items.append(item)
    return items


@router.get("/{report_id}/pending-variants", response_model=list[PendingVariantItem])
def list_pending_variants(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.VARIANTS_INTERPRET)),
) -> list[PendingVariantItem]:
    review = ReviewService(db)
    report = ReportService(db).get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    rows = review.get_pending_variants(report_id)
    return [
        PendingVariantItem(
            annotation_id=ann.id,
            variant=VariantResponse.model_validate(variant),
            gene=ann.gene,
            ml_score=ann.ml_score,
            ml_confidence=ann.ml_confidence,
            clinical_significance=ann.clinical_significance,
            interpretation=ann.interpretation,
            review_status=ann.review_status,
            pharmacogenomic_effect=ann.pharmacogenomic_effect,
        )
        for variant, ann in rows
    ]


@router.post("/{report_id}/variants/{annotation_id}/review", response_model=PendingVariantItem)
def review_variant(
    report_id: uuid.UUID,
    annotation_id: uuid.UUID,
    body: VariantReviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.VARIANTS_INTERPRET)),
) -> PendingVariantItem:
    review = ReviewService(db)
    ann = review.review_variant(report_id, annotation_id, user.id, body.action, body.notes)
    if not ann:
        raise HTTPException(status_code=400, detail="واریانت قابل بررسی نیست")
    variant = db.query(Variant).filter(Variant.id == ann.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="واریانت یافت نشد")
    return PendingVariantItem(
        annotation_id=ann.id,
        variant=VariantResponse.model_validate(variant),
        gene=ann.gene,
        ml_score=ann.ml_score,
        ml_confidence=ann.ml_confidence,
        clinical_significance=ann.clinical_significance,
        interpretation=ann.interpretation,
        review_status=ann.review_status,
        pharmacogenomic_effect=ann.pharmacogenomic_effect,
    )


@router.get("/patient/{patient_id}/variants", response_model=list[VariantWithAnnotation])
def get_patient_variants(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[VariantWithAnnotation]:
    from barekat_genomics.core.rbac import has_permission as hp

    if not (hp(user.role, Permission.VARIANTS_READ) or hp(user.role, Permission.VARIANTS_READ_OWN)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    patient = PatientService(db).get_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="بیمار یافت نشد")
    assert_patient_access(user, patient)
    service = ReportService(db)
    return service.get_patient_variants(patient_id, role=user.role)


@router.post("/{report_id}/approve", response_model=ReportResponse)
def approve_report(
    report_id: uuid.UUID,
    body: ReportApproveRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.REPORTS_APPROVE)),
) -> ReportResponse:
    service = ReportService(db)
    report = service.approve_report(report_id, user.id, body.clinician_notes)
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد یا قابل تأیید نیست")
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/pdf")
def download_report_pdf(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    if not _can_read_reports(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    service = ReportService(db)
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    patient = db.query(Patient).filter(Patient.id == report.patient_id).first()
    if patient:
        assert_patient_access(user, patient)
    if user.role == Role.CLINICIAN.value and not ReviewService(db).clinician_may_view_report(report):
        raise HTTPException(status_code=403, detail="گزارش هنوز تأیید نشده است")
    try:
        pdf_bytes = service.generate_pdf(report_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    filename = f"clinical-report-{str(report_id)[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReportResponse:
    if not _can_read_reports(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    service = ReportService(db)
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    patient = db.query(Patient).filter(Patient.id == report.patient_id).first()
    if patient:
        assert_patient_access(user, patient)
    if user.role == Role.CLINICIAN.value and not ReviewService(db).clinician_may_view_report(report):
        raise HTTPException(status_code=403, detail="گزارش هنوز تأیید نشده است")
    service.get_clinical_content(report)
    return ReportResponse.model_validate(report)

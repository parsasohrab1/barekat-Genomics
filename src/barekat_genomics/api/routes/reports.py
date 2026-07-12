"""Genomic report endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from barekat_genomics.core.database import get_db
from barekat_genomics.schemas import ReportResponse, VariantWithAnnotation
from barekat_genomics.services.report_service import ReportService

router = APIRouter(prefix="/reports")


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)) -> ReportResponse:
    service = ReportService(db)
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد")
    return ReportResponse.model_validate(report)


@router.get("/patient/{patient_id}", response_model=list[ReportResponse])
def list_patient_reports(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[ReportResponse]:
    service = ReportService(db)
    reports = service.list_by_patient(patient_id)
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/patient/{patient_id}/variants", response_model=list[VariantWithAnnotation])
def get_patient_variants(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[VariantWithAnnotation]:
    service = ReportService(db)
    return service.get_patient_variants(patient_id)

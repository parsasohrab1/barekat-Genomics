"""Dashboard statistics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.pipeline import PipelineJob
from barekat_genomics.models.report import GenomicReport
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.variant import Variant, VariantAnnotation
from barekat_genomics.schemas import DashboardStatsResponse

router = APIRouter(prefix="/dashboard")


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.DASHBOARD_READ)),
) -> DashboardStatsResponse:
    total_patients = db.query(func.count(Patient.id)).scalar() or 0
    total_samples = db.query(func.count(SequencingSample.id)).scalar() or 0
    active_pipelines = (
        db.query(func.count(PipelineJob.id))
        .filter(PipelineJob.status.in_(["pending", "running"]))
        .scalar()
        or 0
    )
    completed_reports = (
        db.query(func.count(GenomicReport.id))
        .filter(GenomicReport.status == "completed")
        .scalar()
        or 0
    )
    variants_detected = db.query(func.count(Variant.id)).scalar() or 0
    drug_recommendations = (
        db.query(func.count(GenomicReport.id))
        .filter(GenomicReport.drug_recommendations.isnot(None))
        .scalar()
        or 0
    )

    return DashboardStatsResponse(
        total_patients=total_patients,
        total_samples=total_samples,
        active_pipelines=active_pipelines,
        completed_reports=completed_reports,
        variants_detected=variants_detected,
        drug_recommendations=drug_recommendations,
    )

"""سرویس ثبت دارایی دانشی و مالکیت فکری."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.models.knowledge_asset import KnowledgeAsset

ASSET_TYPES = ("model", "method", "software_kit", "dataset", "guideline")
DISCLOSURE_STATUSES = ("internal", "disclosed", "filed", "granted", "licensed")


class KnowledgeAssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def seed_defaults(self, organization_id: uuid.UUID | None = None) -> list[KnowledgeAsset]:
        defaults = [
            {
                "asset_code": "BG-ML-VCF-V2",
                "title": "Variant Classifier Ensemble v2",
                "title_fa": "طبقه‌بند ensemble واریانت نسخه ۲",
                "asset_type": "model",
                "version": "v2",
                "inventors": "barekat Genomics ML Team",
                "disclosure_status": "internal",
                "license": "Proprietary",
                "linked_artifact": "variant_classifier_v2.pkl",
                "description": "HistGB+RF+XGB+MLP VotingClassifier with SHAP explainability",
            },
            {
                "asset_code": "BG-METHOD-IR-COHORT",
                "title": "Iranian Cohort Biomarker Discovery Method",
                "title_fa": "روش کشف نشانگر کوهورت ایرانی",
                "asset_type": "method",
                "version": "1.0",
                "inventors": "barekat Genomics Clinical Informatics",
                "disclosure_status": "disclosed",
                "license": "Proprietary",
                "linked_artifact": "services/cohort_service.py",
                "description": "Carrier AF + Iranian population enrichment scoring",
            },
            {
                "asset_code": "BG-KIT-PGX-WORKFLOW",
                "title": "Unified WGS/WES/Panel PGx Workflow Kit",
                "title_fa": "کیت نرم‌افزاری workflow یکپارچه WGS/WES/Panel",
                "asset_type": "software_kit",
                "version": "1.0",
                "inventors": "barekat Genomics Engineering",
                "disclosure_status": "internal",
                "license": "Proprietary",
                "linked_artifact": "pipeline/assay_config.py",
                "description": "Assay-aware orchestration with VCF short-circuit and result cache",
            },
        ]
        created = []
        for spec in defaults:
            existing = (
                self.db.query(KnowledgeAsset)
                .filter(KnowledgeAsset.asset_code == spec["asset_code"])
                .first()
            )
            if existing:
                created.append(existing)
                continue
            asset = KnowledgeAsset(organization_id=organization_id, **spec)
            self.db.add(asset)
            created.append(asset)
        self.db.commit()
        return created

    def list(self, organization_id: uuid.UUID | None = None) -> list[KnowledgeAsset]:
        self.seed_defaults(organization_id)
        q = self.db.query(KnowledgeAsset)
        if organization_id is not None:
            q = q.filter(
                (KnowledgeAsset.organization_id == organization_id)
                | (KnowledgeAsset.organization_id.is_(None))
            )
        return q.order_by(KnowledgeAsset.created_at.desc()).all()

    def create(self, **kwargs) -> KnowledgeAsset:
        if kwargs.get("asset_type") not in ASSET_TYPES:
            raise ValueError(f"asset_type نامعتبر — مجاز: {ASSET_TYPES}")
        if kwargs.get("disclosure_status") not in DISCLOSURE_STATUSES:
            raise ValueError(f"disclosure_status نامعتبر — مجاز: {DISCLOSURE_STATUSES}")
        if self.db.query(KnowledgeAsset).filter(KnowledgeAsset.asset_code == kwargs["asset_code"]).first():
            raise ValueError("asset_code تکراری است")
        asset = KnowledgeAsset(**kwargs)
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def update_status(self, asset_id: uuid.UUID, status: str, patent_ref: str | None = None) -> KnowledgeAsset | None:
        if status not in DISCLOSURE_STATUSES:
            raise ValueError(f"وضعیت نامعتبر: {status}")
        asset = self.db.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
        if not asset:
            return None
        asset.disclosure_status = status
        if patent_ref is not None:
            asset.patent_ref = patent_ref
        self.db.commit()
        self.db.refresh(asset)
        return asset

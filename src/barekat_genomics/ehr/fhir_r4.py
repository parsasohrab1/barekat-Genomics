"""سازنده FHIR R4 — Bundle شامل Observation، DiagnosticReport، MedicationRequest."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from barekat_genomics.ehr.models import EHRContext

# LOINC / SNOMED codes
LOINC_PGX_PANEL = "81247-9"
LOINC_GENE_STUDY = "48018-6"
LOINC_VARIANT = "69548-6"
LOINC_EXEC_SUMMARY = "11502-2"
SNOMED_PGX = "118940003"  # Pharmacogenetic test
SNOMED_GENETICS = "108252007"  # Laboratory procedure


def _uuid() -> str:
    return str(uuid.uuid4())


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _patient_resource(ctx: EHRContext) -> dict:
    return {
        "resourceType": "Patient",
        "id": ctx.patient_ehr_id,
        "identifier": [
            {
                "system": "http://barekat.local/patient",
                "value": ctx.patient_external_id,
            },
            {
                "system": "http://barekat.local/ehr",
                "value": ctx.patient_ehr_id,
            },
        ],
    }


def _observation_for_variant(ctx: EHRContext, variant, ann, obs_id: str) -> dict:
    gene = ann.gene if hasattr(ann, "gene") else ann.get("gene")
    rs_id = variant.rs_id if hasattr(variant, "rs_id") else variant.get("rs_id")
    chrom = variant.chromosome if hasattr(variant, "chromosome") else variant["chromosome"]
    pos = variant.position if hasattr(variant, "position") else variant["position"]
    ref = variant.ref_allele if hasattr(variant, "ref_allele") else variant["ref_allele"]
    alt = variant.alt_allele if hasattr(variant, "alt_allele") else variant["alt_allele"]
    sig = ann.clinical_significance if hasattr(ann, "clinical_significance") else ann.get("clinical_significance")
    interp = ann.interpretation if hasattr(ann, "interpretation") else ann.get("interpretation")
    ml_score = ann.ml_score if hasattr(ann, "ml_score") else ann.get("ml_score")

    components = [
        {"code": {"text": "gene"}, "valueString": gene or "unknown"},
        {"code": {"text": "chromosome"}, "valueString": chrom},
        {"code": {"text": "position"}, "valueInteger": pos},
        {"code": {"text": "ref"}, "valueString": ref},
        {"code": {"text": "alt"}, "valueString": alt},
    ]
    if rs_id:
        components.append({"code": {"text": "rsId"}, "valueString": rs_id})
    if ml_score is not None:
        components.append({"code": {"text": "mlScore"}, "valueQuantity": {"value": ml_score, "unit": "1"}})

    return {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": LOINC_VARIANT,
                    "display": "Genetic variant assessment",
                }
            ],
            "text": f"{gene or 'variant'} {rs_id or f'{chrom}:{pos}'}",
        },
        "subject": {"reference": f"Patient/{ctx.patient_ehr_id}"},
        "effectiveDateTime": _iso(ctx.issued_at),
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                    "code": _map_significance(sig),
                    "display": sig or "unknown",
                }
            ],
            "text": interp or "",
        },
        "component": components,
        "note": [{"text": interp}] if interp else [],
    }


def _map_significance(sig: str | None) -> str:
    mapping = {
        "pathogenic": "A",
        "likely_pathogenic": "A",
        "uncertain_significance": "U",
        "benign": "N",
        "likely_benign": "N",
    }
    return mapping.get(sig or "", "U")


def _diagnostic_report(ctx: EHRContext, obs_ids: list[str], report_res_id: str) -> dict:
    clinical = ctx.clinical_content or {}
    summary_parts = clinical.get("executive_summary") or []
    if not summary_parts and ctx.report_summary:
        summary_parts = [ctx.report_summary]

    return {
        "resourceType": "DiagnosticReport",
        "id": report_res_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "GE",
                        "display": "Genetics",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": LOINC_PGX_PANEL,
                    "display": "Pharmacogenomic variant panel",
                },
                {
                    "system": "http://snomed.info/sct",
                    "code": SNOMED_PGX,
                    "display": "Pharmacogenetic test",
                },
            ],
            "text": "Pharmacogenomic genomic report",
        },
        "subject": {"reference": f"Patient/{ctx.patient_ehr_id}"},
        "effectiveDateTime": _iso(ctx.issued_at),
        "issued": _iso(ctx.issued_at),
        "performer": [{"reference": f"Organization/{ctx.organization_id}"}],
        "result": [{"reference": f"Observation/{oid}"} for oid in obs_ids],
        "conclusion": " ".join(summary_parts) if summary_parts else ctx.report_summary or "",
        "conclusionCode": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": SNOMED_GENETICS,
                        "display": "Laboratory procedure",
                    }
                ]
            }
        ],
    }


def _medication_requests(ctx: EHRContext) -> list[dict]:
    drugs = []
    clinical = ctx.clinical_content or {}
    enriched = clinical.get("drug_recommendations") or []

    if enriched:
        for d in enriched:
            drugs.append(d)
    elif ctx.drug_recommendations:
        for drug_name, rec in ctx.drug_recommendations.items():
            drugs.append({"drug": drug_name, **rec})

    requests = []
    for drug in drugs:
        drug_name = drug.get("drug") or drug.get("drug_fa") or "unknown"
        med_id = _uuid()
        requests.append(
            {
                "resourceType": "MedicationRequest",
                "id": med_id,
                "status": "active",
                "intent": "proposal",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
                                "code": "community",
                                "display": "Community",
                            }
                        ]
                    }
                ],
                "medicationCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": drug_name.lower().replace(" ", ""),
                            "display": drug.get("drug_fa") or drug_name,
                        }
                    ],
                    "text": drug_name,
                },
                "subject": {"reference": f"Patient/{ctx.patient_ehr_id}"},
                "authoredOn": _iso(ctx.issued_at),
                "requester": {"reference": f"Organization/{ctx.organization_id}"},
                "reasonCode": [
                    {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": SNOMED_PGX,
                                "display": "Pharmacogenetic finding",
                            }
                        ],
                        "text": drug.get("gene") or "pharmacogenomics",
                    }
                ],
                "dosageInstruction": [
                    {
                        "text": drug.get("recommendation") or drug.get("action_fa") or "",
                        "patientInstruction": drug.get("action_fa") or drug.get("recommendation") or "",
                    }
                ],
                "note": [
                    {
                        "text": (
                            f"CPIC level: {drug.get('cpic_level', 'C')} — "
                            f"{drug.get('cpic_guideline', '')}"
                        ).strip(" —"),
                    }
                ],
            }
        )
    return requests


def _organization_resource(ctx: EHRContext) -> dict:
    return {
        "resourceType": "Organization",
        "id": ctx.organization_id,
        "name": "barekat Genomics",
        "type": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/organization-type",
                        "code": "prov",
                        "display": "Healthcare Provider",
                    }
                ]
            }
        ],
    }


def build_fhir_bundle(ctx: EHRContext) -> dict:
    """ساخت Bundle نوع collection با Patient، Observations، DiagnosticReport، MedicationRequest."""
    entries: list[dict] = []
    obs_ids: list[str] = []
    report_res_id = ctx.report_id or _uuid()

    entries.append({"fullUrl": f"urn:uuid:org-{ctx.organization_id}", "resource": _organization_resource(ctx)})
    entries.append({"fullUrl": f"Patient/{ctx.patient_ehr_id}", "resource": _patient_resource(ctx)})

    for variant in ctx.variants:
        annotations = variant.annotations if hasattr(variant, "annotations") else variant.get("annotations", [])
        if not annotations:
            continue
        ann = annotations[0]
        obs_id = _uuid()
        obs_ids.append(obs_id)
        entries.append(
            {
                "fullUrl": f"Observation/{obs_id}",
                "resource": _observation_for_variant(ctx, variant, ann, obs_id),
            }
        )

    if obs_ids:
        entries.append(
            {
                "fullUrl": f"DiagnosticReport/{report_res_id}",
                "resource": _diagnostic_report(ctx, obs_ids, report_res_id),
            }
        )

    for med in _medication_requests(ctx):
        entries.append({"fullUrl": f"MedicationRequest/{med['id']}", "resource": med})

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": _iso(ctx.issued_at),
        "identifier": {
            "system": "http://barekat.local/fhir/bundle",
            "value": report_res_id,
        },
        "entry": entries,
    }

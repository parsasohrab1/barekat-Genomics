"""دریافت FHIR Bundle و ایجاد/به‌روزرسانی بیمار."""

from __future__ import annotations

import uuid
from typing import Any


def parse_fhir_patient_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """استخراج اطلاعات Patient از Bundle یا منبع Patient واحد."""
    resources: list[dict] = []
    if bundle.get("resourceType") == "Bundle":
        for entry in bundle.get("entry") or []:
            res = entry.get("resource") or {}
            if res.get("resourceType"):
                resources.append(res)
    elif bundle.get("resourceType") == "Patient":
        resources.append(bundle)
    else:
        raise ValueError("ورودی باید Bundle یا Patient باشد")

    patient_res = next((r for r in resources if r.get("resourceType") == "Patient"), None)
    if not patient_res:
        raise ValueError("منبع Patient در FHIR یافت نشد")

    external_id = None
    for ident in patient_res.get("identifier") or []:
        val = ident.get("value")
        if val:
            external_id = str(val)
            break
    if not external_id:
        external_id = patient_res.get("id") or f"fhir-{uuid.uuid4().hex[:12]}"

    name = None
    for n in patient_res.get("name") or []:
        parts = []
        if n.get("family"):
            parts.append(n["family"])
        parts.extend(n.get("given") or [])
        if parts:
            name = " ".join(parts)
            break

    gender = patient_res.get("gender")
    gender_map = {"male": "male", "female": "female", "other": "other", "unknown": None}
    gender = gender_map.get(gender, gender) if gender else None

    ehr_id = patient_res.get("id")
    return {
        "external_id": external_id,
        "full_name": name,
        "gender": gender,
        "ehr_patient_id": ehr_id,
        "resource_count": len(resources),
        "raw_patient": patient_res,
    }

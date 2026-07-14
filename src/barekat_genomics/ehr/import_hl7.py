"""دریافت HL7 v2 (ADT/ORU) و استخراج PID."""

from __future__ import annotations

import re


def parse_hl7_message(message: str) -> dict:
    """پارس ساده HL7 v2 با جداکننده | و ^."""
    text = message.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ValueError("پیام HL7 خالی است")

    segments = [line for line in text.split("\n") if line.strip()]
    msh = next((s for s in segments if s.startswith("MSH")), None)
    pid = next((s for s in segments if s.startswith("PID")), None)
    if not pid:
        raise ValueError("سگمنت PID یافت نشد")

    fields = pid.split("|")
    # PID-3 patient identifier list, PID-5 name, PID-8 sex
    id_field = fields[3] if len(fields) > 3 else ""
    name_field = fields[5] if len(fields) > 5 else ""
    sex_field = fields[8] if len(fields) > 8 else ""

    external_id = id_field.split("^")[0].split("~")[0].strip() or None
    name_parts = [p for p in name_field.split("^") if p]
    # HL7 often Family^Given
    full_name = " ".join(reversed(name_parts[:2])) if name_parts else None
    if not full_name and name_parts:
        full_name = " ".join(name_parts)

    sex_map = {"M": "male", "F": "female", "O": "other", "U": None}
    gender = sex_map.get(sex_field.strip().upper()[:1], None)

    msg_type = None
    if msh:
        msh_fields = msh.split("|")
        # MSH-9 message type
        if len(msh_fields) > 8:
            msg_type = msh_fields[8].split("^")[0]

    if not external_id:
        raise ValueError("شناسه بیمار در PID-3 یافت نشد")

    return {
        "external_id": external_id,
        "full_name": full_name,
        "gender": gender,
        "ehr_patient_id": external_id,
        "message_type": msg_type,
        "segment_count": len(segments),
    }


def is_hl7_payload(text: str) -> bool:
    return bool(re.search(r"(?m)^MSH\|", text or ""))

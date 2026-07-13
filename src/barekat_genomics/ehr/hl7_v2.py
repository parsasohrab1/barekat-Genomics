"""سازنده پیام HL7 v2 ORU^R01 برای سیستم‌های قدیمی."""

from __future__ import annotations

from datetime import datetime, timezone

from barekat_genomics.ehr.models import EHRContext

FIELD_SEP = "|"
COMP_SEP = "^"
SUBCOMP_SEP = "&"
REP_SEP = "~"
ESC_SEP = "\\"


def _hl7_ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def _escape(value: str) -> str:
    return (
        value.replace(ESC_SEP, ESC_SEP * 2 + "E" + ESC_SEP)
        .replace(FIELD_SEP, ESC_SEP + "F" + ESC_SEP)
        .replace(COMP_SEP, ESC_SEP + "S" + ESC_SEP)
        .replace(REP_SEP, ESC_SEP + "R" + ESC_SEP)
        .replace(SUBCOMP_SEP, ESC_SEP + "T" + ESC_SEP)
    )


def _msh(ctx: EHRContext, msg_id: str, receiving: str) -> str:
  sending = ctx.organization_id.upper()
  return FIELD_SEP.join(
      [
          "MSH",
          f"{COMP_SEP}~{SUBCOMP_SEP}{REP_SEP}{ESC_SEP}",
          sending,
          "GENOMICS",
          receiving,
          "HIS",
          _hl7_ts(ctx.issued_at),
          "",
          "ORU^R01^ORU_R01",
          msg_id,
          "P",
          "2.5",
          "",
          "",
          "",
          "UTF-8",
      ]
  )


def _pid(ctx: EHRContext) -> str:
    return FIELD_SEP.join(
        [
            "PID",
            "1",
            "",
            f"{ctx.patient_ehr_id}^^^{sending_facility(ctx)}^MR",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ctx.patient_external_id,
        ]
    )


def sending_facility(ctx: EHRContext) -> str:
    return ctx.organization_id.upper()


def _obr(ctx: EHRContext, set_id: int = 1) -> str:
    return FIELD_SEP.join(
        [
            "OBR",
            str(set_id),
            ctx.report_id or "",
            "",
            f"81247-9{COMP_SEP}Pharmacogenomic Panel{COMP_SEP}LN",
            "",
            _hl7_ts(ctx.issued_at),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            _hl7_ts(ctx.issued_at),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "F",
            "",
            "",
            "",
            "",
            "",
            "Pharmacogenomic genomic report",
        ]
    )


def _obx_variant(set_id: int, variant, ann) -> str:
    gene = ann.gene if hasattr(ann, "gene") else ann.get("gene")
    rs_id = variant.rs_id if hasattr(variant, "rs_id") else variant.get("rs_id")
    chrom = variant.chromosome if hasattr(variant, "chromosome") else variant["chromosome"]
    pos = variant.position if hasattr(variant, "position") else variant["position"]
    ref = variant.ref_allele if hasattr(variant, "ref_allele") else variant["ref_allele"]
    alt = variant.alt_allele if hasattr(variant, "alt_allele") else variant["alt_allele"]
    sig = ann.clinical_significance if hasattr(ann, "clinical_significance") else ann.get("clinical_significance")
    interp = ann.interpretation if hasattr(ann, "interpretation") else ann.get("interpretation") or ""
    ml = ann.ml_score if hasattr(ann, "ml_score") else ann.get("ml_score")

    value = (
        f"{gene or 'GENE'}{COMP_SEP}{rs_id or f'{chrom}:{pos}'}{COMP_SEP}"
        f"{ref}>{alt}{COMP_SEP}{sig or 'unknown'}"
    )
    if ml is not None:
        value += f"{COMP_SEP}ML={ml:.3f}"

    return FIELD_SEP.join(
        [
            "OBX",
            str(set_id),
            "CE",
            f"69548-6{COMP_SEP}Genetic variant{COMP_SEP}LN",
            "",
            _escape(value),
            "",
            "",
            "",
            "",
            "F",
            "",
            "",
            _hl7_ts(datetime.now(timezone.utc)),
            "",
            "",
            "",
            "",
            "",
            _escape(interp[:200]),
        ]
    )


def _obx_drug(set_id: int, drug: dict) -> str:
    drug_name = drug.get("drug") or drug.get("drug_fa") or "unknown"
    rec = drug.get("recommendation") or drug.get("action_fa") or ""
    level = drug.get("cpic_level") or "C"
    gene = drug.get("gene") or ""
    value = f"{drug_name}{COMP_SEP}{gene}{COMP_SEP}CPIC-{level}{COMP_SEP}{_escape(rec[:120])}"

    return FIELD_SEP.join(
        [
            "OBX",
            str(set_id),
            "TX",
            f"MEDREQ{COMP_SEP}Medication recommendation{COMP_SEP}BAREKAT",
            "",
            _escape(value),
            "",
            "",
            "",
            "",
            "F",
        ]
    )


def _obx_summary(set_id: int, text: str) -> str:
    return FIELD_SEP.join(
        [
            "OBX",
            str(set_id),
            "TX",
            f"11502-2{COMP_SEP}Laboratory report{COMP_SEP}LN",
            "",
            _escape(text[:500]),
            "",
            "",
            "",
            "",
            "F",
        ]
    )


def build_oru_message(ctx: EHRContext, *, receiving_facility: str = "HIS") -> str:
    """ساخت پیام ORU^R01 با سگمنت‌های MSH، PID، OBR و OBX."""
    msg_id = (ctx.report_id or _hl7_ts(ctx.issued_at))[:20]
    segments = [_msh(ctx, msg_id, receiving_facility), _pid(ctx), _obr(ctx)]

    obx_id = 1
    clinical = ctx.clinical_content or {}
    summary_parts = clinical.get("executive_summary") or []
    if summary_parts:
        segments.append(_obx_summary(obx_id, " ".join(summary_parts)))
        obx_id += 1
    elif ctx.report_summary:
        segments.append(_obx_summary(obx_id, ctx.report_summary))
        obx_id += 1

    for variant in ctx.variants:
        annotations = variant.annotations if hasattr(variant, "annotations") else variant.get("annotations", [])
        if not annotations:
            continue
        segments.append(_obx_variant(obx_id, variant, annotations[0]))
        obx_id += 1

    drugs = clinical.get("drug_recommendations") or []
    if not drugs and ctx.drug_recommendations:
        drugs = [{"drug": k, **v} for k, v in ctx.drug_recommendations.items()]
    for drug in drugs:
        segments.append(_obx_drug(obx_id, drug))
        obx_id += 1

    return "\r".join(segments) + "\r"

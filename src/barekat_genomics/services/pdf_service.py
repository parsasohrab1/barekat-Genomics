"""Generate the clinical report PDF with logo and digital signature."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from fpdf import FPDF

from barekat_genomics.core.config import get_settings

# Possible Persian font paths
_FONT_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "assets" / "fonts" / "Vazirmatn-Regular.ttf",
    Path("C:/Windows/Fonts/tahoma.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansArabic-Regular.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"),
]


def _find_font() -> Path | None:
    for path in _FONT_CANDIDATES:
        if path.exists():
            return path
    return None


def _shape_persian(text: str) -> str:
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(str(text)))
    except ImportError:
        return str(text)


def _multi_line(pdf: FPDF, text: str, h: float = 6, size: int | None = None) -> None:
    if size:
        pdf.set_font("Clinical", size=size)
    pdf.set_x(pdf.l_margin)
    try:
        pdf.multi_cell(pdf.epw, h, _shape_persian(text), align="R")
    except Exception:
        pdf.multi_cell(pdf.epw, h, str(text), align="L")


def _truncate(text: str, max_len: int = 50) -> str:
    s = str(text)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def compute_report_signature(report_id: str, clinical_content: dict, approver_id: str | None) -> str:
    settings = get_settings()
    payload = json.dumps(
        {"report_id": report_id, "content": clinical_content, "approver": approver_id},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hmac.new(
        settings.secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


class ClinicalReportPDF(FPDF):
    def __init__(self, font_path: Path) -> None:
        super().__init__()
        self.font_path = font_path
        self._font_registered = False

    def _ensure_font(self) -> None:
        if not self._font_registered:
            self.add_font("Clinical", "", str(self.font_path))
            self._font_registered = True

    def header(self) -> None:
        self._ensure_font()
        self.set_fill_color(37, 99, 235)
        self.rect(0, 0, 210, 28, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Clinical", size=16)
        self.set_xy(10, 8)
        self.cell(0, 10, _shape_persian("barekat Genomics"), align="R")
        self.set_font("Clinical", size=9)
        self.set_xy(10, 18)
        self.cell(0, 6, _shape_persian("Clinical Pharmacogenomic Report"), align="R")
        self.ln(22)
        self.set_text_color(30, 41, 59)

    def footer(self) -> None:
        self.set_y(-18)
        self.set_font("Clinical", size=8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, _shape_persian(f"Page {self.page_no()}"), align="C")
        self.ln(4)
        self.cell(0, 5, "barekat Genomics Platform — Confidential PHI", align="C")


def generate_clinical_pdf(
    *,
    report_id: str,
    patient_external_id: str,
    clinical_content: dict,
    report_status: str,
    created_at: datetime,
    approved_at: datetime | None,
    approver_name: str | None,
    digital_signature: str | None,
) -> bytes:
    font_path = _find_font()
    if not font_path:
        raise RuntimeError(
            "Persian font not found. Place the Vazirmatn font in assets/fonts "
            "or install fonts-noto-core on the system."
        )

    pdf = ClinicalReportPDF(font_path)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Clinical", size=10)

    # Header information
    pdf.set_font("Clinical", size=11)
    pdf.cell(0, 8, _shape_persian(f"Report ID: {report_id[:8]}..."), ln=True, align="R")
    pdf.cell(0, 7, _shape_persian(f"Patient: {patient_external_id}"), ln=True, align="R")
    pdf.cell(
        0,
        7,
        _shape_persian(f"Date: {created_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"),
        ln=True,
        align="R",
    )
    status_fa = "Final" if report_status == "completed" else "Pending approval"
    pdf.cell(0, 7, _shape_persian(f"Status: {status_fa}"), ln=True, align="R")
    schema_ver = clinical_content.get("schema_version", "1.0")
    pdf.cell(0, 7, _shape_persian(f"Report schema version: {schema_ver}"), ln=True, align="R")
    meta = clinical_content.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("genome_build"):
        pdf.cell(0, 7, _shape_persian(f"Reference genome: {meta['genome_build']}"), ln=True, align="R")
    pdf.ln(6)

    # Executive summary
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Clinical", size=12)
    pdf.cell(0, 9, _shape_persian("Executive summary"), ln=True, align="R", fill=True)
    pdf.ln(2)
    pdf.set_font("Clinical", size=10)
    for sentence in clinical_content.get("executive_summary", []):
        _multi_line(pdf, sentence, h=7)
        pdf.ln(2)
    pdf.ln(4)

    # High-priority variants table
    hp_variants = clinical_content.get("high_priority_variants", [])
    pdf.set_font("Clinical", size=12)
    pdf.cell(
        0,
        9,
        _shape_persian(f"High-significance variants ({len(hp_variants)})"),
        new_x="LMARGIN",
        new_y="NEXT",
        align="R",
        fill=True,
    )
    pdf.ln(2)
    pdf.set_font("Clinical", size=7)
    epw = pdf.epw
    col_w = [epw * 0.1, epw * 0.12, epw * 0.14, epw * 0.16, epw * 0.1, epw * 0.38]
    headers = ["Gene", "rsID", "Position", "Significance", "Priority", "Interpretation"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, _shape_persian(h), border=1, align="C")
    pdf.ln()
    for v in hp_variants:
        loc = f"{v.get('chromosome')}:{v.get('position')}"
        sig = v.get("clinical_significance", "")
        prio = f"{(v.get('priority_score', 0) * 100):.0f}%"
        interp = _truncate(v.get("interpretation") or "", 60)
        row = [
            v.get("gene") or "-",
            v.get("rs_id") or "-",
            loc,
            sig,
            prio,
            interp,
        ]
        for i, cell in enumerate(row):
            try:
                pdf.cell(col_w[i], 7, _shape_persian(str(cell)), border=1, align="R")
            except Exception:
                pdf.cell(col_w[i], 7, _truncate(str(cell), 20), border=1, align="L")
        pdf.ln()
    pdf.ln(4)

    # Explainability for high-priority variants
    explained = [v for v in hp_variants if v.get("feature_contributions")]
    if explained:
        pdf.set_font("Clinical", size=12)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 9, _shape_persian("Model decision transparency (Explainability)"), ln=True, align="R", fill=True)
        pdf.ln(2)
        pdf.set_font("Clinical", size=9)
        for v in explained[:5]:
            gene = v.get("gene") or "-"
            method = v.get("explain_method") or "feature_importance"
            pdf.cell(0, 6, _shape_persian(f"{gene} ({v.get('rs_id') or '-'}) — method: {method}"), ln=True, align="R")
            feats = ", ".join(
                f"{f.get('feature')}:{(f.get('contribution') or 0) * 100:.0f}%"
                for f in (v.get("feature_contributions") or [])[:4]
                if isinstance(f, dict)
            )
            if feats:
                pdf.cell(0, 6, feats, ln=True, align="L")
            pdf.ln(1)
        pdf.ln(2)

    # Biomarker panel
    panel = clinical_content.get("biomarker_panel") or {}
    markers = panel.get("ranked_markers") or []
    if markers:
        pdf.set_font("Clinical", size=12)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(
            0,
            9,
            _shape_persian(
                f"Biomarker panel (ranked — {panel.get('high_priority_count', 0)} high priority)"
            ),
            ln=True,
            align="R",
            fill=True,
        )
        pdf.ln(2)
        pdf.set_font("Clinical", size=8)
        for m in markers[:8]:
            line = (
                f"#{m.get('rank') or '-'} {m.get('gene') or '-'} / {m.get('rs_id') or '-'} "
                f"— ML={(m.get('ml_score') or 0) * 100:.0f}%"
            )
            pdf.cell(0, 6, _shape_persian(line), ln=True, align="R")
        pdf.ln(3)

    # CPIC drug recommendations
    drugs = clinical_content.get("drug_recommendations", [])
    pdf.set_font("Clinical", size=12)
    pdf.cell(0, 9, _shape_persian("Drug recommendations (CPIC)"), ln=True, align="R", fill=True)
    pdf.ln(2)
    pdf.set_font("Clinical", size=9)
    for d in drugs:
        drug_line = f"{d.get('drug_fa', d.get('drug'))} — gene {d.get('gene')}"
        pdf.set_font("Clinical", size=10)
        pdf.cell(0, 7, _shape_persian(drug_line), ln=True, align="R")
        pdf.set_font("Clinical", size=9)
        level = d.get("cpic_level_label") or f"Level {d.get('cpic_level')}"
        pdf.cell(0, 6, _shape_persian(f"Evidence level: {level}"), ln=True, align="R")
        if d.get("cpic_guideline"):
            pdf.cell(0, 6, d.get("cpic_guideline", ""), ln=True, align="L")
        if d.get("recommendation"):
            _multi_line(pdf, d["recommendation"], h=6, size=9)
        if d.get("action_fa"):
            _multi_line(pdf, f"Action: {d['action_fa']}", h=6, size=9)
        pdf.ln(3)

    # Drug interaction warnings
    interactions = clinical_content.get("drug_interactions", [])
    pdf.set_font("Clinical", size=12)
    pdf.set_fill_color(254, 226, 226)
    pdf.cell(
        0,
        9,
        _shape_persian(f"Drug interaction warnings ({len(interactions)})"),
        new_x="LMARGIN",
        new_y="NEXT",
        align="R",
        fill=True,
    )
    pdf.ln(2)
    pdf.set_font("Clinical", size=9)
    if not interactions:
        pdf.cell(0, 7, _shape_persian("No significant interaction was identified."), new_x="LMARGIN", new_y="NEXT", align="R")
    else:
        for ix in interactions:
            drugs_fa = " + ".join(ix.get("drugs_fa", ix.get("drugs", [])))
            sev = ix.get("severity_label", ix.get("severity"))
            pdf.set_font("Clinical", size=10)
            pdf.cell(0, 7, _shape_persian(f"{drugs_fa} — severity: {sev}"), new_x="LMARGIN", new_y="NEXT", align="R")
            _multi_line(pdf, ix.get("warning_fa", ""), h=6, size=9)
            _multi_line(pdf, f"Recommendation: {ix.get('recommendation_fa', '')}", h=6, size=9)
            pdf.ln(3)

    # Digital signature
    pdf.ln(6)
    pdf.set_fill_color(236, 253, 245)
    pdf.set_font("Clinical", size=11)
    pdf.cell(0, 9, _shape_persian("Digital signature"), new_x="LMARGIN", new_y="NEXT", align="R", fill=True)
    pdf.ln(2)
    pdf.set_font("Clinical", size=8)
    sig = digital_signature or compute_report_signature(report_id, clinical_content, None)
    _multi_line(pdf, f"Signature (HMAC-SHA256): {sig[:48]}...", h=5, size=8)
    if approver_name and approved_at:
        pdf.cell(
            0,
            5,
            _shape_persian(
                f"Approved by: {approver_name} — "
                f"{approved_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
            ),
            ln=True,
            align="R",
        )
    pdf.cell(
        0,
        5,
        _shape_persian("This document was generated electronically and signed with the server key."),
        ln=True,
        align="R",
    )

    buf = BytesIO()
    out = pdf.output(buf)
    if out is None:
        return buf.getvalue()
    return bytes(out) if isinstance(out, (bytes, bytearray)) else buf.getvalue()

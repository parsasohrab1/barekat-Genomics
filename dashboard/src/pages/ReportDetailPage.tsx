import { useEffect, useState } from "react";

import { Link, useParams } from "react-router-dom";

import { AlertTriangle, ArrowRight, CheckCircle, Download, FileText, Pill } from "lucide-react";

import { approveReport, askVariant, downloadReportPdf, getPendingVariants, getPlainSummary, getReport, getPatients, reviewVariant } from "../lib/api";

import { useAuth } from "../context/AuthContext";

import { cpicLevelClass, formatDateTime, interactionSeverityClass, sigClass, sigLabel } from "../lib/format";

import type { ClinicalReportContent, PendingVariantItem, PlainSummary, Report } from "../lib/types";



export default function ReportDetailPage() {

  const { id } = useParams<{ id: string }>();

  const { hasRole } = useAuth();

  const [report, setReport] = useState<Report | null>(null);

  const [patientLabel, setPatientLabel] = useState("");

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [approving, setApproving] = useState(false);

  const [pdfLoading, setPdfLoading] = useState(false);

  const [pendingVariants, setPendingVariants] = useState<PendingVariantItem[]>([]);

  const [reviewLoading, setReviewLoading] = useState<string | null>(null);
  const [plainSummary, setPlainSummary] = useState<PlainSummary | null>(null);
  const [plainLoading, setPlainLoading] = useState(false);
  const [askRsId, setAskRsId] = useState("");
  const [askQuestion, setAskQuestion] = useState("");
  const [askAnswer, setAskAnswer] = useState("");
  const [askLoading, setAskLoading] = useState(false);



  const canApprove = hasRole("geneticist", "admin");

  const canReviewVariants = canApprove && report?.status === "pending_genetic_review";

  const clinical: ClinicalReportContent | null = report?.clinical_content ?? null;



  useEffect(() => {

    if (!id) return;

    setLoading(true);

    getReport(id)

      .then(async (r) => {

        setReport(r);

        const patients = await getPatients();

        const p = patients.find((x) => x.id === r.patient_id);

        setPatientLabel(p?.external_id ?? r.patient_id.slice(0, 8));

        if (r.status === "pending_genetic_review") {

          const pending = await getPendingVariants(id);

          setPendingVariants(pending);

        }

      })

      .catch(() => setError("Report not found"))

      .finally(() => setLoading(false));

  }, [id]);



  async function handleVariantReview(annotationId: string, action: "approved" | "rejected") {

    if (!id) return;

    setReviewLoading(annotationId);

    try {

      const updated = await reviewVariant(id, annotationId, action);

      const nextPending = pendingVariants.map((v) => (v.annotation_id === annotationId ? updated : v));

      setPendingVariants(nextPending);

      const stillPending = nextPending.some((v) => v.review_status === "pending");

      if (!stillPending) {

        const refreshed = await getReport(id);

        setReport(refreshed);

      }

    } catch {

      setError("Variant review failed");

    } finally {

      setReviewLoading(null);

    }

  }



  async function handleApprove() {

    if (!id || !report) return;

    setApproving(true);

    try {

      const updated = await approveReport(id);

      setReport(updated);

    } catch {

      setError("Report approval failed");

    } finally {

      setApproving(false);

    }

  }



  async function handlePdfDownload() {

    if (!id) return;

    setPdfLoading(true);

    try {

      const blob = await downloadReportPdf(id);

      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");

      a.href = url;

      a.download = `clinical-report-${id.slice(0, 8)}.pdf`;

      a.click();

      URL.revokeObjectURL(url);

    } catch {

      setError("Error generating PDF");

    } finally {

      setPdfLoading(false);

    }

  }



  if (loading) return <p className="text-sm text-slate-400">Loading report...</p>;

  if (error || !report) return <p className="text-sm text-rose-600">{error || "Error"}</p>;



  const statusLabel =

    report.status === "completed"

      ? "Final"

      : report.status === "pending_genetic_review"

        ? "Awaiting geneticist review"

        : report.status === "pending_review"

          ? "Ready for final approval"

          : "Draft";



  const executiveSummary = clinical?.executive_summary ?? (report.summary ? [report.summary] : []);

  const hpVariants = clinical?.high_priority_variants ?? [];
  const biomarkerPanel = clinical?.biomarker_panel ?? null;
  const rankedMarkers = biomarkerPanel?.ranked_markers ?? [];

  const drugRecs = clinical?.drug_recommendations ?? [];

  const interactions = clinical?.drug_interactions ?? [];



  return (

    <div className="space-y-6">

      <div className="flex flex-wrap items-center justify-between gap-3">

        <Link to="/reports" className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline">

          <ArrowRight className="h-4 w-4" />

          Back to reports

        </Link>

        <div className="flex gap-2">

          <button

            onClick={handlePdfDownload}

            disabled={pdfLoading}

            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50 disabled:opacity-60"

          >

            <Download className="h-3.5 w-3.5" />

            {pdfLoading ? "Generating..." : "Download PDF"}

          </button>

          {canApprove && report.status === "pending_review" && (

            <button

              onClick={handleApprove}

              disabled={approving}

              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-60"

            >

              <CheckCircle className="h-3.5 w-3.5" />

              {approving ? "Approving..." : "Approve report"}

            </button>

          )}

        </div>

      </div>



      {/* Header */}

      <div className="stat-card">

        <div className="flex items-start justify-between gap-4">

          <div>

            <h2 className="text-lg font-bold text-slate-800">Report {report.report_type}</h2>

            <p className="text-sm text-slate-400">Patient: {patientLabel}</p>

          </div>

          <span className={report.status === "completed" ? "badge-success" : "badge-warning"}>

            {statusLabel}

          </span>

        </div>

        <p className="mt-2 text-xs text-slate-400">

          Created: {formatDateTime(report.created_at)}

          {report.finalized_at && ` — Finalized: ${formatDateTime(report.finalized_at)}`}

        </p>

      </div>



      {canReviewVariants && pendingVariants.length > 0 && (

        <div className="stat-card border-amber-200 bg-amber-50/30">

          <h3 className="mb-4 text-sm font-semibold text-amber-900">

            Variants requiring review (ML score &gt; 0.7)

          </h3>

          <div className="space-y-3">

            {pendingVariants.map((pv) => (

              <div key={pv.annotation_id} className="rounded-lg border border-amber-100 bg-white p-4">

                <div className="flex flex-wrap items-start justify-between gap-3">

                  <div>

                    <p className="font-medium text-slate-800">

                      {pv.gene ?? "—"} — {pv.variant.rs_id ?? `${pv.variant.chromosome}:${pv.variant.position}`}

                    </p>

                    <p className="text-xs text-slate-500">{pv.interpretation}</p>

                    <p className="mt-1 text-xs text-brand-700">

                      ML score: {((pv.ml_score ?? 0) * 100).toFixed(0)}%

                    </p>

                  </div>

                  <div className="flex items-center gap-2">

                    {pv.review_status === "pending" ? (

                      <>

                        <button

                          onClick={() => handleVariantReview(pv.annotation_id, "approved")}

                          disabled={reviewLoading === pv.annotation_id}

                          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs text-white hover:bg-emerald-700 disabled:opacity-60"

                        >

                          Approve

                        </button>

                        <button

                          onClick={() => handleVariantReview(pv.annotation_id, "rejected")}

                          disabled={reviewLoading === pv.annotation_id}

                          className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs text-white hover:bg-rose-700 disabled:opacity-60"

                        >

                          Reject

                        </button>

                      </>

                    ) : (

                      <span className={pv.review_status === "approved" ? "badge-success" : "badge-warning"}>

                        {pv.review_status === "approved" ? "Approved" : "Rejected"}

                      </span>

                    )}

                  </div>

                </div>

              </div>

            ))}

          </div>

        </div>

      )}



      {/* Executive summary */}

      <div className="stat-card">

        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">

          <FileText className="h-4 w-4 text-brand-600" />

          Executive summary

        </h3>

        <div className="space-y-2">

          {executiveSummary.map((sentence, i) => (

            <p key={i} className="text-sm leading-relaxed text-slate-700">

              {sentence}

            </p>

          ))}

        </div>

      </div>



      {/* Plain-language summary — decision support */}
      <div className="stat-card border-amber-100 bg-amber-50/40">
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Plain-language summary (decision support)</h3>
        <p className="mb-3 text-xs text-amber-700">Not a direct diagnosis — only an aid to clinical decision-making</p>
        {!plainSummary ? (
          <button
            onClick={async () => {
              if (!id) return;
              setPlainLoading(true);
              try {
                setPlainSummary(await getPlainSummary(id));
              } catch {
                setError("Error generating plain summary");
              } finally {
                setPlainLoading(false);
              }
            }}
            disabled={plainLoading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {plainLoading ? "Generating..." : "Show plain summary"}
          </button>
        ) : (
          <div className="space-y-2">
            {plainSummary.plain_summary.map((p, i) => (
              <p key={i} className="text-sm leading-relaxed text-slate-700">{p}</p>
            ))}
            <p className="mt-2 text-xs text-slate-500">{plainSummary.disclaimer}</p>
          </div>
        )}
        <div className="mt-4 border-t border-amber-100 pt-4">
          <p className="mb-2 text-xs font-medium text-slate-600">Question about a variant (PharmGKB)</p>
          <div className="flex flex-wrap gap-2">
            <input
              value={askRsId}
              onChange={(e) => setAskRsId(e.target.value)}
              placeholder="rs4244285"
              className="rounded border px-2 py-1 text-sm"
            />
            <input
              value={askQuestion}
              onChange={(e) => setAskQuestion(e.target.value)}
              placeholder="Physician's question..."
              className="min-w-[200px] flex-1 rounded border px-2 py-1 text-sm"
            />
            <button
              onClick={async () => {
                if (!askRsId || !askQuestion) return;
                setAskLoading(true);
                setAskAnswer("");
                try {
                  const res = await askVariant(askQuestion, askRsId);
                  setAskAnswer(res.answer_fa);
                } catch {
                  setAskAnswer("Error answering");
                } finally {
                  setAskLoading(false);
                }
              }}
              disabled={askLoading || !askRsId || !askQuestion}
              className="rounded-lg border border-brand-600 px-3 py-1 text-sm text-brand-700 disabled:opacity-50"
            >
              {askLoading ? "..." : "Ask"}
            </button>
          </div>
          {askAnswer && <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{askAnswer}</p>}
        </div>
      </div>



      {/* High-significance variants table */}

      <div className="stat-card">

        <h3 className="mb-4 text-sm font-semibold text-slate-700">

          High-significance variants ({hpVariants.length})

        </h3>

        {hpVariants.length === 0 ? (

          <p className="text-sm text-slate-400">No high-priority variants found.</p>

        ) : (

          <div className="overflow-x-auto">

            <table className="data-table">

              <thead>

                <tr>

                  <th>Rank</th>

                  <th>Gene</th>

                  <th>rsID</th>

                  <th>Position</th>

                  <th>Significance</th>

                  <th>Priority</th>

                  <th>Model explanation</th>

                  <th>Interpretation</th>

                </tr>

              </thead>

              <tbody>

                {hpVariants.map((v, idx) => (

                  <tr key={`${v.rs_id}-${idx}`}>

                    <td className="font-mono text-xs">{v.rank ?? idx + 1}</td>

                    <td className="font-medium text-brand-700">{v.gene ?? "—"}</td>

                    <td className="font-mono text-xs">{v.rs_id ?? "—"}</td>

                    <td className="font-mono text-xs">{v.chromosome}:{v.position}</td>

                    <td>

                      <span className={sigClass[v.clinical_significance] ?? "badge-info"}>

                        {sigLabel[v.clinical_significance] ?? v.clinical_significance}

                      </span>

                    </td>

                    <td>{(v.priority_score * 100).toFixed(0)}%</td>

                    <td className="max-w-[10rem] text-xs text-slate-500">
                      {(v.feature_contributions ?? [])
                        .slice(0, 3)
                        .map((f) => `${f.feature}${f.contribution != null ? `:${(f.contribution * 100).toFixed(0)}%` : ""}`)
                        .join(" · ") || (v.explain_method ?? "—")}
                    </td>

                    <td className="max-w-xs text-xs text-slate-600">{v.interpretation ?? "—"}</td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </div>

      {/* Biomarker panel and ranking */}
      <div className="stat-card">
        <h3 className="mb-4 text-sm font-semibold text-slate-700">
          Biomarker panel ({biomarkerPanel?.total_variants ?? rankedMarkers.length})
        </h3>
        {rankedMarkers.length === 0 ? (
          <p className="text-sm text-slate-400">No ranked biomarkers available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Gene / rsID</th>
                  <th>ML score</th>
                  <th>Guideline drugs</th>
                  <th>Sources</th>
                  <th>Influential features</th>
                </tr>
              </thead>
              <tbody>
                {rankedMarkers.slice(0, 20).map((m, idx) => (
                  <tr key={`${m.rs_id}-${idx}`} className={m.high_priority ? "bg-amber-50/40" : undefined}>
                    <td className="font-mono text-xs">{m.rank ?? idx + 1}</td>
                    <td>
                      <div className="font-medium text-brand-700">{m.gene ?? "—"}</div>
                      <div className="font-mono text-xs text-slate-500">{m.rs_id ?? "—"}</div>
                    </td>
                    <td>{m.ml_score != null ? (m.ml_score * 100).toFixed(0) + "%" : "—"}</td>
                    <td className="text-xs text-slate-600">{(m.guideline_drugs ?? []).join(", ") || "—"}</td>
                    <td className="text-xs text-slate-500">{(m.knowledge_sources ?? []).join(", ") || "—"}</td>
                    <td className="text-xs text-slate-500">
                      {(m.top_features ?? [])
                        .map((f) => f.feature)
                        .slice(0, 3)
                        .join(" · ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>



      {/* CPIC drug recommendations */}

      <div className="stat-card">

        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-700">

          <Pill className="h-4 w-4 text-brand-600" />

          Drug recommendations (CPIC guideline)

        </h3>

        {drugRecs.length === 0 ? (

          <p className="text-sm text-slate-400">No actionable drug recommendation found.</p>

        ) : (

          <div className="space-y-3">

            {drugRecs.map((d) => (

              <div key={d.drug} className="rounded-lg border border-slate-100 bg-slate-50 p-4">

                <div className="flex flex-wrap items-center justify-between gap-2">

                  <p className="font-medium text-slate-800">

                    {d.drug_fa ?? d.drug}

                    <span className="mr-2 text-xs text-slate-400">({d.drug})</span>

                  </p>

                  {d.cpic_level && (

                    <span className={cpicLevelClass[d.cpic_level] ?? "badge-info"}>

                      {d.cpic_level_label ?? `Level ${d.cpic_level}`}

                    </span>

                  )}

                </div>

                <p className="mt-1 text-xs text-brand-700">Gene: {d.gene}</p>

                {d.cpic_guideline && (

                  <p className="mt-1 text-xs text-slate-500">{d.cpic_guideline}</p>

                )}

                <p className="mt-2 text-sm text-slate-600">{d.recommendation}</p>

                {d.action_fa && (

                  <p className="mt-2 text-sm font-medium text-emerald-800">Action: {d.action_fa}</p>

                )}

                <p className="mt-1 text-xs text-slate-400">

                  ML confidence: {((d.confidence ?? 0) * 100).toFixed(0)}%

                </p>

              </div>

            ))}

          </div>

        )}

      </div>



      {/* Drug interaction warnings */}

      <div className="stat-card border-rose-100">

        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-700">

          <AlertTriangle className="h-4 w-4 text-rose-600" />

          Drug interaction warnings ({interactions.length})

        </h3>

        {interactions.length === 0 ? (

          <p className="text-sm text-slate-500">No significant drug interaction was identified among the recommended drugs.</p>

        ) : (

          <div className="space-y-3">

            {interactions.map((ix, i) => (

              <div key={i} className="rounded-lg border border-rose-100 bg-rose-50/50 p-4">

                <div className="flex items-center justify-between">

                  <p className="font-medium text-slate-800">

                    {(ix.drugs_fa ?? ix.drugs).join(" + ")}

                  </p>

                  <span className={interactionSeverityClass[ix.severity] ?? "badge-warning"}>

                    {ix.severity_label ?? ix.severity}

                  </span>

                </div>

                <p className="mt-2 text-sm text-rose-800">{ix.warning_fa}</p>

                <p className="mt-1 text-sm text-slate-600">Recommendation: {ix.recommendation_fa}</p>

              </div>

            ))}

          </div>

        )}

      </div>



      {/* Digital signature */}

      {clinical?.digital_signature && (

        <div className="stat-card border-emerald-100 bg-emerald-50/30">

          <h3 className="mb-2 text-sm font-semibold text-emerald-800">Digital signature</h3>

          <p className="font-mono text-xs text-slate-600 break-all">

            {clinical.digital_signature.signature.slice(0, 64)}...

          </p>

          {clinical.digital_signature.signed_at && (

            <p className="mt-1 text-xs text-slate-500">

              Signed at: {formatDateTime(clinical.digital_signature.signed_at)}

            </p>

          )}

        </div>

      )}

    </div>

  );

}


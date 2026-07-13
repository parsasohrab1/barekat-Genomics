import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Eye, ChevronDown } from "lucide-react";
import { downloadReportPdf, exportEhr, exportEhrFhir, exportEhrHl7, getReports, getPatients } from "../lib/api";
import { formatDate } from "../lib/format";
import type { Report } from "../lib/types";

type EhrFormat = "json" | "fhir" | "hl7";

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [patients, setPatients] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getReports(), getPatients()])
      .then(([r, p]) => {
        setReports(r);
        setPatients(Object.fromEntries(p.map((x) => [x.id, x.external_id])));
      })
      .catch(() => setError("خطا در بارگذاری گزارش‌ها"))
      .finally(() => setLoading(false));
  }, []);

  const handlePdfDownload = async (reportId: string) => {
    try {
      const blob = await downloadReportPdf(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `clinical-report-${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("خطا در تولید PDF");
    }
  };

  const handleEhrExport = async (patientId: string, format: EhrFormat = "json") => {
    try {
      let blob: Blob;
      let filename: string;
      if (format === "fhir") {
        blob = await exportEhrFhir(patientId);
        filename = `fhir-${patientId.slice(0, 8)}.json`;
      } else if (format === "hl7") {
        blob = await exportEhrHl7(patientId);
        filename = `oru-${patientId.slice(0, 8)}.hl7`;
      } else {
        const data = await exportEhr(patientId);
        blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        filename = `ehr-export-${patientId.slice(0, 8)}.json`;
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("خطا در خروجی EHR");
    }
  };

  if (loading) return <p className="text-sm text-slate-400">در حال بارگذاری...</p>;
  if (error) return <p className="text-sm text-rose-600">{error}</p>;

  return (
    <div className="space-y-4">
      {reports.length === 0 ? (
        <p className="stat-card text-center text-sm text-slate-400">
          گزارشی موجود نیست — ابتدا پایپ‌لاین را اجرا کنید
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {reports.map((r) => (
            <div key={r.id} className="stat-card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-slate-700">{r.id.slice(0, 8)}...</p>
                  <p className="text-xs text-slate-400">
                    بیمار: {patients[r.patient_id] ?? r.patient_id.slice(0, 8)} — {r.report_type}
                  </p>
                </div>
                <span className={r.status === "completed" ? "badge-success" : "badge-warning"}>
                  {r.status === "completed"
                    ? "نهایی"
                    : r.status === "pending_genetic_review"
                      ? "در انتظار ژنتیک‌دان"
                      : r.status === "pending_review"
                        ? "آماده تأیید"
                        : "پیش‌نویس"}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-600">{r.summary ?? "—"}</p>
              {r.variant_summary && (
                <p className="mt-1 text-xs text-slate-400">
                  {r.variant_summary.total_variants} واریانت — {r.variant_summary.high_priority} با اولویت بالا
                </p>
              )}
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-slate-400">{formatDate(r.created_at)}</span>
                <div className="flex gap-2">
                  <Link
                    to={`/reports/${r.id}`}
                    className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    مشاهده
                  </Link>
                  <button
                    onClick={() => handlePdfDownload(r.id)}
                    className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                  >
                    <Download className="h-3.5 w-3.5" />
                    PDF
                  </button>
                  <div className="relative group">
                    <button
                      type="button"
                      className="flex items-center gap-1 rounded-lg bg-brand-50 px-3 py-1.5 text-xs text-brand-700 hover:bg-brand-100"
                    >
                      <Download className="h-3.5 w-3.5" />
                      EHR
                      <ChevronDown className="h-3 w-3" />
                    </button>
                    <div className="absolute left-0 top-full z-10 mt-1 hidden min-w-[140px] rounded-lg border border-slate-200 bg-white py-1 shadow-lg group-hover:block group-focus-within:block">
                      <button
                        type="button"
                        onClick={() => handleEhrExport(r.patient_id, "json")}
                        className="block w-full px-3 py-1.5 text-right text-xs hover:bg-slate-50"
                      >
                        JSON
                      </button>
                      <button
                        type="button"
                        onClick={() => handleEhrExport(r.patient_id, "fhir")}
                        className="block w-full px-3 py-1.5 text-right text-xs hover:bg-slate-50"
                      >
                        FHIR R4
                      </button>
                      <button
                        type="button"
                        onClick={() => handleEhrExport(r.patient_id, "hl7")}
                        className="block w-full px-3 py-1.5 text-right text-xs hover:bg-slate-50"
                      >
                        HL7 ORU
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

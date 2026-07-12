import { Download, Eye } from "lucide-react";

const reports = [
  { id: "RPT-301", patient: "P0001", type: "فارماکوژنومیک", status: "completed", summary: "۷ واریانت — ۲ توصیه دارویی", date: "2026-07-12" },
  { id: "RPT-300", patient: "P0003", type: "فارماکوژنومیک", status: "completed", summary: "۵ واریانت — ۱ توصیه دارویی", date: "2026-07-11" },
  { id: "RPT-299", patient: "P0002", type: "ژنومی", status: "draft", summary: "در حال تولید...", date: "2026-07-11" },
  { id: "RPT-298", patient: "P0004", type: "فارماکوژنومیک", status: "completed", summary: "۳ واریانت — بدون توصیه", date: "2026-07-10" },
];

export default function ReportsPage() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {reports.map((r) => (
          <div key={r.id} className="stat-card">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-slate-700">{r.id}</p>
                <p className="text-xs text-slate-400">بیمار: {r.patient} — {r.type}</p>
              </div>
              <span className={r.status === "completed" ? "badge-success" : "badge-warning"}>
                {r.status === "completed" ? "نهایی" : "پیش‌نویس"}
              </span>
            </div>
            <p className="mt-3 text-sm text-slate-600">{r.summary}</p>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-slate-400">{r.date}</span>
              <div className="flex gap-2">
                <button className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50">
                  <Eye className="h-3.5 w-3.5" />
                  مشاهده
                </button>
                <button className="flex items-center gap-1 rounded-lg bg-brand-50 px-3 py-1.5 text-xs text-brand-700 hover:bg-brand-100">
                  <Download className="h-3.5 w-3.5" />
                  EHR
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

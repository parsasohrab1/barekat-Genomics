import { Play, RefreshCw } from "lucide-react";

const jobs = [
  { id: "JOB-441", sample: "S-2024-0888", stage: "variant_calling", status: "running", progress: 65 },
  { id: "JOB-440", sample: "S-2024-0891", stage: "quality_control", status: "running", progress: 30 },
  { id: "JOB-439", sample: "S-2024-0887", stage: "done", status: "completed", progress: 100 },
  { id: "JOB-438", sample: "S-2024-0885", stage: "interpretation", status: "completed", progress: 100 },
  { id: "JOB-437", sample: "S-2024-0880", stage: "quality_control", status: "failed", progress: 15 },
];

const stageLabel: Record<string, string> = {
  queued: "در صف",
  quality_control: "کنترل کیفیت",
  variant_calling: "شناسایی واریانت",
  interpretation: "تفسیر",
  done: "تکمیل",
};

const statusClass: Record<string, string> = {
  running: "badge-info",
  completed: "badge-success",
  failed: "badge-danger",
  pending: "badge-warning",
};

export default function PipelinePage() {
  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <button className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm hover:bg-slate-50">
          <RefreshCw className="h-4 w-4" />
          بروزرسانی
        </button>
        <button className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          <Play className="h-4 w-4" />
          اجرای پایپ‌لاین
        </button>
      </div>

      <div className="grid gap-4">
        {jobs.map((job) => (
          <div key={job.id} className="stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-700">{job.id}</p>
                <p className="text-xs text-slate-400">نمونه: {job.sample}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="badge-info">{stageLabel[job.stage]}</span>
                <span className={statusClass[job.status]}>
                  {job.status === "running" ? "در حال اجرا" : job.status === "completed" ? "تکمیل" : "خطا"}
                </span>
              </div>
            </div>
            <div className="mt-3">
              <div className="flex justify-between text-xs text-slate-400">
                <span>پیشرفت</span>
                <span>{job.progress}%</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full transition-all ${
                    job.status === "failed" ? "bg-rose-500" : "bg-brand-500"
                  }`}
                  style={{ width: `${job.progress}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

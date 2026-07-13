import { useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { getModules, getPipelineJobs, getSamples, startPipeline } from "../lib/api";
import { usePolling } from "../hooks/usePolling";
import { formatDateTime, jobStatusClass, jobStatusLabel, stageLabel } from "../lib/format";
import type { GenomicsModule, PipelineJob, Sample } from "../lib/types";
import Modal from "../components/ui/Modal";

const MODULE_LABELS: Record<string, string> = {
  pharmacogenomics: "فارماکوژنومیک",
  pgx_panel: "پنل CPIC",
  cgp: "پروفایل سرطان",
  carrier_screening: "غربالگری ناقل",
  tumor_normal: "تومور/نرمال",
  prs: "PRS",
};

export default function PipelinePage() {
  const [jobs, setJobs] = useState<PipelineJob[]>([]);
  const [error, setError] = useState("");
  const [runModal, setRunModal] = useState(false);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [modules, setModules] = useState<GenomicsModule[]>([]);
  const [selectedSample, setSelectedSample] = useState("");
  const [selectedModule, setSelectedModule] = useState("pharmacogenomics");
  const [pairedSample, setPairedSample] = useState("");
  const [running, setRunning] = useState(false);

  const load = () =>
    getPipelineJobs()
      .then(setJobs)
      .catch(() => setError("خطا در بارگذاری پایپ‌لاین"));

  usePolling(getPipelineJobs, setJobs, 4000);

  const hasActive = jobs.some((j) => j.status === "running" || j.status === "pending");
  const selectedMod = modules.find((m) => m.id === selectedModule);

  const openRunModal = async () => {
    try {
      const [s, m] = await Promise.all([getSamples(), getModules()]);
      setSamples(s.filter((x) => x.status === "uploaded"));
      setModules(m);
      setRunModal(true);
    } catch {
      setError("خطا در بارگذاری نمونه‌ها");
    }
  };

  const handleRun = async () => {
    if (!selectedSample) return;
    if (selectedMod?.requires_paired_sample && !pairedSample) {
      setError("این ماژول نیاز به نمونه جفت دارد");
      return;
    }
    setRunning(true);
    setError("");
    try {
      await startPipeline(selectedSample, true, {
        module: selectedModule,
        paired_sample_id: pairedSample || undefined,
      });
      setRunModal(false);
      setSelectedSample("");
      setPairedSample("");
      await load();
    } catch {
      setError("خطا در اجرای پایپ‌لاین");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className={`h-2 w-2 rounded-full ${hasActive ? "animate-pulse bg-brand-500" : "bg-slate-300"}`} />
          {hasActive ? "بروزرسانی خودکار هر ۴ ثانیه" : "بدون وظیفه فعال"}
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm hover:bg-slate-50">
            <RefreshCw className="h-4 w-4" />
            بروزرسانی
          </button>
          <button onClick={openRunModal} className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
            <Play className="h-4 w-4" />
            اجرای پایپ‌لاین
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="grid gap-4">
        {jobs.length === 0 ? (
          <p className="stat-card text-center text-sm text-slate-400">وظیفه‌ای ثبت نشده</p>
        ) : (
          jobs.map((job) => (
            <div key={job.id} className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-700">{job.id.slice(0, 8)}...</p>
                  <p className="text-xs text-slate-400">
                    نمونه: {job.sample_label ?? job.sample_id.slice(0, 8)}
                    {job.module && ` — ${MODULE_LABELS[job.module] ?? job.module}`}
                    {job.created_at && ` — ${formatDateTime(job.created_at)}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge-info">{stageLabel[job.stage] ?? job.stage}</span>
                  <span className={jobStatusClass[job.status] ?? "badge-warning"}>
                    {jobStatusLabel[job.status] ?? job.status}
                  </span>
                </div>
              </div>
              <div className="mt-3">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>پیشرفت</span>
                  <span>{job.progress ?? 0}%</span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      job.status === "failed" ? "bg-rose-500" : "bg-brand-500"
                    }`}
                    style={{ width: `${job.progress ?? 0}%` }}
                  />
                </div>
              </div>
              {job.error_message && (
                <p className="mt-2 text-xs text-rose-600">{job.error_message}</p>
              )}
            </div>
          ))
        )}
      </div>

      <Modal open={runModal} onClose={() => setRunModal(false)} title="اجرای پایپ‌لاین">
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-slate-600">ماژول تشخیصی</label>
            <select
              value={selectedModule}
              onChange={(e) => {
                setSelectedModule(e.target.value);
                setPairedSample("");
              }}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              {modules.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name_fa} ({m.gene_count > 0 ? `${m.gene_count} ژن` : "PRS"})
                </option>
              ))}
            </select>
            {selectedMod && (
              <p className="mt-1 text-xs text-slate-400">{selectedMod.description_fa}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-600">انتخاب نمونه (آپلود شده)</label>
            <select
              value={selectedSample}
              onChange={(e) => setSelectedSample(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">—</option>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.sample_id} ({s.patient_external_id})
                </option>
              ))}
            </select>
          </div>
          {selectedMod?.requires_paired_sample && (
            <div>
              <label className="mb-1 block text-sm text-slate-600">نمونه نرمال (جفت)</label>
              <select
                value={pairedSample}
                onChange={(e) => setPairedSample(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="">—</option>
                {samples
                  .filter((s) => s.id !== selectedSample)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.sample_id} ({s.patient_external_id})
                    </option>
                  ))}
              </select>
            </div>
          )}
          {samples.length === 0 && (
            <p className="text-sm text-amber-600">نمونه آپلود‌شده‌ای وجود ندارد</p>
          )}
          <div className="flex justify-end gap-2">
            <button onClick={() => setRunModal(false)} className="rounded-lg border px-4 py-2 text-sm">انصراف</button>
            <button
              onClick={handleRun}
              disabled={!selectedSample || running}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {running ? "در حال اجرا..." : "شروع پردازش"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

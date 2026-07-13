import { useEffect, useState } from "react";
import { Upload } from "lucide-react";
import SampleUploadModal from "../components/forms/SampleUploadModal";
import { getSamples } from "../lib/api";
import { formatDate, sampleStatusMap } from "../lib/format";
import type { Sample } from "../lib/types";

export default function SamplesPage() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    getSamples()
      .then(setSamples)
      .catch(() => setError("خطا در بارگذاری نمونه‌ها"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          <Upload className="h-4 w-4" />
          آپلود نمونه
        </button>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-card">
        {loading ? (
          <p className="p-8 text-center text-sm text-slate-400">در حال بارگذاری...</p>
        ) : samples.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">نمونه‌ای ثبت نشده</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>شناسه نمونه</th>
                <th>بیمار</th>
                <th>نوع فایل</th>
                <th>نسخه ژنوم</th>
                <th>تاریخ</th>
                <th>وضعیت</th>
              </tr>
            </thead>
            <tbody>
              {samples.map((s) => {
                const st = sampleStatusMap[s.status] ?? { label: s.status, class: "badge-info" };
                return (
                  <tr key={s.id}>
                    <td className="font-medium text-brand-700">{s.sample_id}</td>
                    <td>{s.patient_external_id ?? s.patient_id.slice(0, 8)}</td>
                    <td><span className="badge-info">{s.file_type}</span></td>
                    <td>{s.genome_build}</td>
                    <td>{formatDate(s.created_at)}</td>
                    <td><span className={st.class}>{st.label}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <SampleUploadModal open={modalOpen} onClose={() => setModalOpen(false)} onSuccess={load} />
    </div>
  );
}

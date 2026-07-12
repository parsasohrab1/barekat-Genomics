import { Upload } from "lucide-react";

const samples = [
  { id: "S-2024-0887", patient: "P0001", type: "BAM", status: "processed", build: "GRCh38", date: "2026-07-12" },
  { id: "S-2024-0888", patient: "P0002", type: "FASTQ", status: "processing", build: "GRCh38", date: "2026-07-12" },
  { id: "S-2024-0889", patient: "P0003", type: "BAM", status: "uploaded", build: "GRCh38", date: "2026-07-11" },
  { id: "S-2024-0890", patient: "P0004", type: "FASTQ", status: "processed", build: "GRCh38", date: "2026-07-11" },
  { id: "S-2024-0891", patient: "P0005", type: "BAM", status: "processing", build: "GRCh38", date: "2026-07-10" },
];

const statusMap: Record<string, { label: string; class: string }> = {
  processed: { label: "پردازش‌شده", class: "badge-success" },
  processing: { label: "در حال پردازش", class: "badge-info" },
  uploaded: { label: "آپلود شده", class: "badge-warning" },
  failed: { label: "خطا", class: "badge-danger" },
};

export default function SamplesPage() {
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          <Upload className="h-4 w-4" />
          آپلود نمونه
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-card">
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
            {samples.map((s) => (
              <tr key={s.id}>
                <td className="font-medium text-brand-700">{s.id}</td>
                <td>{s.patient}</td>
                <td><span className="badge-info">{s.type}</span></td>
                <td>{s.build}</td>
                <td>{s.date}</td>
                <td><span className={statusMap[s.status].class}>{statusMap[s.status].label}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

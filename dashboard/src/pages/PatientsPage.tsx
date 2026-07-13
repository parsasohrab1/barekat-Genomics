import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import PatientFormModal from "../components/forms/PatientFormModal";
import { getPatients } from "../lib/api";
import { formatDate } from "../lib/format";
import type { Patient } from "../lib/types";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    getPatients()
      .then(setPatients)
      .catch(() => setError("خطا در بارگذاری بیماران — API در دسترس نیست"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = patients.filter(
    (p) =>
      p.external_id.includes(search) ||
      (p.ehr_patient_id?.includes(search) ?? false)
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="جستجوی بیمار..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent text-sm outline-none sm:w-64"
          />
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
        >
          <Plus className="h-4 w-4" />
          بیمار جدید
        </button>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <div className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-card">
        {loading ? (
          <p className="p-8 text-center text-sm text-slate-400">در حال بارگذاری...</p>
        ) : filtered.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">بیماری یافت نشد</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>شناسه</th>
                <th>سن</th>
                <th>جنسیت</th>
                <th>شناسه EHR</th>
                <th>تاریخ ثبت</th>
                <th>وضعیت</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id}>
                  <td className="font-medium text-brand-700">{p.external_id}</td>
                  <td>{p.age ?? "—"}</td>
                  <td>{p.gender === "Male" ? "مرد" : p.gender === "Female" ? "زن" : "—"}</td>
                  <td>{p.ehr_patient_id ?? "—"}</td>
                  <td>{formatDate(p.created_at)}</td>
                  <td><span className="badge-success">فعال</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <PatientFormModal open={modalOpen} onClose={() => setModalOpen(false)} onSuccess={load} />
    </div>
  );
}

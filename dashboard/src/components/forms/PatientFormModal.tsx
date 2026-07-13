import { useState } from "react";
import Modal from "../ui/Modal";
import { createPatient, ApiClientError } from "../../lib/api";
import type { PatientCreate } from "../../lib/types";

interface PatientFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function PatientFormModal({ open, onClose, onSuccess }: PatientFormModalProps) {
  const [form, setForm] = useState<PatientCreate>({
    external_id: "",
    name: "",
    age: undefined,
    gender: "",
    ehr_patient_id: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await createPatient({
        external_id: form.external_id,
        name: form.name || undefined,
        age: form.age ? Number(form.age) : undefined,
        gender: form.gender || undefined,
        ehr_patient_id: form.ehr_patient_id || undefined,
      });
      onSuccess();
      onClose();
      setForm({ external_id: "", name: "", age: undefined, gender: "", ehr_patient_id: "" });
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "خطا در ثبت بیمار");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="ثبت بیمار جدید">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="شناسه بیمار *" value={form.external_id} onChange={(v) => setForm({ ...form, external_id: v })} required />
        <Field label="نام" value={form.name ?? ""} onChange={(v) => setForm({ ...form, name: v })} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="سن" value={String(form.age ?? "")} onChange={(v) => setForm({ ...form, age: v ? Number(v) : undefined })} type="number" />
          <div>
            <label className="mb-1 block text-sm text-slate-600">جنسیت</label>
            <select
              value={form.gender ?? ""}
              onChange={(e) => setForm({ ...form, gender: e.target.value })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            >
              <option value="">—</option>
              <option value="Male">مرد</option>
              <option value="Female">زن</option>
            </select>
          </div>
        </div>
        <Field label="شناسه EHR" value={form.ehr_patient_id ?? ""} onChange={(v) => setForm({ ...form, ehr_patient_id: v })} />
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50">
            انصراف
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {loading ? "در حال ثبت..." : "ثبت بیمار"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm text-slate-600">{label}</label>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
      />
    </div>
  );
}

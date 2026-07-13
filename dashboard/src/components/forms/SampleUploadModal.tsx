import { useEffect, useState } from "react";
import Modal from "../ui/Modal";
import { getPatients, uploadSample, ApiClientError } from "../../lib/api";
import type { Patient } from "../../lib/types";

interface SampleUploadModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function SampleUploadModal({ open, onClose, onSuccess }: SampleUploadModalProps) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState("");
  const [sampleId, setSampleId] = useState("");
  const [fileType, setFileType] = useState<"FASTQ" | "BAM">("FASTQ");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) getPatients().then(setPatients).catch(() => setPatients([]));
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("فایل را انتخاب کنید");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await uploadSample(patientId, sampleId, fileType, file);
      onSuccess();
      onClose();
      setPatientId("");
      setSampleId("");
      setFile(null);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "خطا در آپلود");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="آپلود نمونه توالی‌یابی">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm text-slate-600">بیمار *</label>
          <select
            required
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          >
            <option value="">انتخاب بیمار...</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.external_id} {p.ehr_patient_id ? `(${p.ehr_patient_id})` : ""}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">شناسه نمونه *</label>
          <input
            required
            value={sampleId}
            onChange={(e) => setSampleId(e.target.value)}
            placeholder="S-2024-0001"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">نوع فایل *</label>
          <select
            value={fileType}
            onChange={(e) => setFileType(e.target.value as "FASTQ" | "BAM")}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          >
            <option value="FASTQ">FASTQ</option>
            <option value="BAM">BAM</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">فایل *</label>
          <input
            type="file"
            required
            accept=".fastq,.fq,.fastq.gz,.bam"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm"
          />
        </div>
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
            {loading ? "در حال آپلود..." : "آپلود"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

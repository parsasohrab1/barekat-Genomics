export interface Patient {
  id: string;
  external_id: string;
  age: number | null;
  gender: string | null;
  ehr_patient_id: string | null;
  created_at: string;
}

export interface PipelineJob {
  id: string;
  sample_id: string;
  stage: string;
  status: string;
  created_at: string;
}

export interface Report {
  id: string;
  patient_id: string;
  report_type: string;
  status: string;
  summary: string | null;
  created_at: string;
}

export interface DashboardStats {
  totalPatients: number;
  totalSamples: number;
  activePipelines: number;
  completedReports: number;
  variantsDetected: number;
  drugRecommendations: number;
}

export interface ActivityItem {
  id: string;
  type: "pipeline" | "report" | "sample" | "patient";
  title: string;
  description: string;
  time: string;
  status: "success" | "running" | "pending" | "failed";
}

export interface VariantItem {
  id: string;
  gene: string;
  rs_id: string;
  chromosome: string;
  position: number;
  clinical_significance: string;
  priority_score: number;
  drug: string;
}

export const mockStats: DashboardStats = {
  totalPatients: 500,
  totalSamples: 342,
  activePipelines: 8,
  completedReports: 287,
  variantsDetected: 12450,
  drugRecommendations: 156,
};

export const mockActivities: ActivityItem[] = [
  {
    id: "1",
    type: "pipeline",
    title: "پایپ‌لاین P0247 تکمیل شد",
    description: "۷ واریانت با اولویت بالا شناسایی شد",
    time: "۵ دقیقه پیش",
    status: "success",
  },
  {
    id: "2",
    type: "report",
    title: "گزارش فارماکوژنومیک صادر شد",
    description: "بیمار P0183 — ۳ توصیه دارویی",
    time: "۱۲ دقیقه پیش",
    status: "success",
  },
  {
    id: "3",
    type: "sample",
    title: "نمونه BAM آپلود شد",
    description: "S-2024-0891 — GRCh38",
    time: "۲۵ دقیقه پیش",
    status: "running",
  },
  {
    id: "4",
    type: "pipeline",
    title: "کنترل کیفیت در حال اجرا",
    description: "S-2024-0892 — FASTQ",
    time: "۳۲ دقیقه پیش",
    status: "running",
  },
  {
    id: "5",
    type: "patient",
    title: "بیمار جدید ثبت شد",
    description: "P0501 — EHR-77821",
    time: "۱ ساعت پیش",
    status: "pending",
  },
];

export const mockPatients: Patient[] = [
  { id: "1", external_id: "P0001", age: 52, gender: "Female", ehr_patient_id: "EHR-10001", created_at: "2026-07-10" },
  { id: "2", external_id: "P0002", age: 64, gender: "Male", ehr_patient_id: "EHR-10002", created_at: "2026-07-10" },
  { id: "3", external_id: "P0003", age: 77, gender: "Female", ehr_patient_id: "EHR-10003", created_at: "2026-07-11" },
  { id: "4", external_id: "P0004", age: 51, gender: "Female", ehr_patient_id: null, created_at: "2026-07-11" },
  { id: "5", external_id: "P0005", age: 45, gender: "Male", ehr_patient_id: "EHR-10005", created_at: "2026-07-12" },
];

export const mockVariants: VariantItem[] = [
  { id: "1", gene: "CYP2C19", rs_id: "rs4244285", chromosome: "chr10", position: 96521657, clinical_significance: "pathogenic", priority_score: 0.92, drug: "clopidogrel" },
  { id: "2", gene: "CYP2C9", rs_id: "rs1799853", chromosome: "chr10", position: 96702047, clinical_significance: "pathogenic", priority_score: 0.88, drug: "warfarin" },
  { id: "3", gene: "TPMT", rs_id: "rs1142345", chromosome: "chr6", position: 18130918, clinical_significance: "likely_pathogenic", priority_score: 0.85, drug: "azathioprine" },
  { id: "4", gene: "DPYD", rs_id: "rs1800460", chromosome: "chr1", position: 97915614, clinical_significance: "pathogenic", priority_score: 0.91, drug: "fluorouracil" },
  { id: "5", gene: "MTHFR", rs_id: "rs1801133", chromosome: "chr1", position: 11796321, clinical_significance: "likely_pathogenic", priority_score: 0.72, drug: "methotrexate" },
];

export const monthlyData = [
  { month: "فروردین", samples: 42, reports: 38 },
  { month: "اردیبهشت", samples: 58, reports: 51 },
  { month: "خرداد", samples: 65, reports: 60 },
  { month: "تیر", samples: 72, reports: 68 },
  { month: "مرداد", samples: 80, reports: 74 },
  { month: "شهریور", samples: 88, reports: 82 },
];

export const variantTypeData = [
  { name: "SNP", value: 78, color: "#0891b2" },
  { name: "Indel", value: 15, color: "#6366f1" },
  { name: "سایر", value: 7, color: "#94a3b8" },
];

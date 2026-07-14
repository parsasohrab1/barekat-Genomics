export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("fa-IR");
  } catch {
    return iso;
  }
}

export function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("fa-IR");
  } catch {
    return iso;
  }
}

export const sampleStatusMap: Record<string, { label: string; class: string }> = {
  processed: { label: "پردازش‌شده", class: "badge-success" },
  processing: { label: "در حال پردازش", class: "badge-info" },
  uploaded: { label: "آپلود شده", class: "badge-warning" },
  failed: { label: "خطا", class: "badge-danger" },
};

export const stageLabel: Record<string, string> = {
  queued: "در صف",
  quality_control: "کنترل کیفیت",
  alignment: "هم‌ترازسازی",
  variant_calling: "شناسایی واریانت",
  interpretation: "تفسیر",
  done: "تکمیل",
};

export const jobStatusClass: Record<string, string> = {
  running: "badge-info",
  completed: "badge-success",
  failed: "badge-danger",
  pending: "badge-warning",
};

export const jobStatusLabel: Record<string, string> = {
  running: "در حال اجرا",
  completed: "تکمیل",
  failed: "خطا",
  pending: "در انتظار",
};

export const sigClass: Record<string, string> = {
  pathogenic: "badge-danger",
  likely_pathogenic: "badge-warning",
  uncertain_significance: "badge-info",
  benign: "badge-success",
};

export const sigLabel: Record<string, string> = {
  pathogenic: "بیماری‌زا",
  likely_pathogenic: "احتمال بیماری‌زا",
  uncertain_significance: "نامشخص",
  benign: "خنثی",
};

export const cpicLevelClass: Record<string, string> = {
  A: "badge-success",
  B: "badge-info",
  C: "badge-warning",
  D: "badge-danger",
};

export const interactionSeverityClass: Record<string, string> = {
  major: "badge-danger",
  moderate: "badge-warning",
  minor: "badge-info",
};

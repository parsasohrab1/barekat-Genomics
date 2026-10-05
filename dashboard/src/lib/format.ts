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
  processed: { label: "Processed", class: "badge-success" },
  processing: { label: "Processing", class: "badge-info" },
  uploaded: { label: "Uploaded", class: "badge-warning" },
  failed: { label: "Error", class: "badge-danger" },
};

export const stageLabel: Record<string, string> = {
  queued: "Queued",
  quality_control: "Quality control",
  alignment: "Alignment",
  variant_calling: "Variant calling",
  interpretation: "Interpretation",
  done: "Done",
};

export const jobStatusClass: Record<string, string> = {
  running: "badge-info",
  completed: "badge-success",
  failed: "badge-danger",
  pending: "badge-warning",
};

export const jobStatusLabel: Record<string, string> = {
  running: "Running",
  completed: "Completed",
  failed: "Error",
  pending: "Pending",
};

export const sigClass: Record<string, string> = {
  pathogenic: "badge-danger",
  likely_pathogenic: "badge-warning",
  uncertain_significance: "badge-info",
  benign: "badge-success",
};

export const sigLabel: Record<string, string> = {
  pathogenic: "Pathogenic",
  likely_pathogenic: "Likely pathogenic",
  uncertain_significance: "Uncertain",
  benign: "Benign",
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

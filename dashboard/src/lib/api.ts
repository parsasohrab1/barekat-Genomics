import type {

  DashboardStats,

  Patient,

  PatientCreate,

  PipelineJob,
  GenomicsModule,
  PlainSummary,
  VariantAskResult,

  Report,

  Sample,

  User,

  Variant,

  AuditLog,

  TokenResponse,

} from "./types";



const API_BASE = "/api/v1";



let authToken: string | null = null;



export function setAuthToken(token: string | null) {

  authToken = token;

}



class ApiClientError extends Error {

  constructor(

    message: string,

    public status: number

  ) {

    super(message);

    this.name = "ApiClientError";

  }

}



async function request<T>(url: string, options?: RequestInit): Promise<T> {

  const headers = new Headers(options?.headers);

  if (authToken) {

    headers.set("Authorization", `Bearer ${authToken}`);

  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {

    let detail = res.statusText;

    try {

      const body = await res.json();

      detail = body.detail ?? detail;

    } catch {

      /* ignore */

    }

    throw new ApiClientError(String(detail), res.status);

  }

  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;

}



// --- Auth ---

export async function login(email: string, password: string): Promise<TokenResponse> {

  const form = new URLSearchParams();

  form.append("username", email);

  form.append("password", password);

  return request<TokenResponse>(`${API_BASE}/auth/login`, {

    method: "POST",

    headers: { "Content-Type": "application/x-www-form-urlencoded" },

    body: form,

  });

}



export async function getMe(): Promise<User> {

  return request<User>(`${API_BASE}/auth/me`);

}



export async function getHealth(): Promise<boolean> {

  try {

    const data = await request<{ status: string }>(`${API_BASE}/health`);

    return data.status === "healthy";

  } catch {

    return false;

  }

}



export async function getDashboardStats(): Promise<DashboardStats> {

  return request<DashboardStats>(`${API_BASE}/dashboard/stats`);

}



// --- Patients ---

export async function getPatients(): Promise<Patient[]> {

  return request<Patient[]>(`${API_BASE}/patients/`);

}



export async function createPatient(data: PatientCreate): Promise<Patient> {

  return request<Patient>(`${API_BASE}/patients/`, {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify(data),

  });

}



// --- Samples ---

export async function getSamples(): Promise<Sample[]> {

  return request<Sample[]>(`${API_BASE}/samples/`);

}



export async function uploadSample(

  patientId: string,

  sampleId: string,

  fileType: string,

  file: File

): Promise<Sample> {

  const form = new FormData();

  form.append("patient_id", patientId);

  form.append("sample_id", sampleId);

  form.append("file_type", fileType);

  form.append("file", file);

  return request<Sample>(`${API_BASE}/samples/upload`, { method: "POST", body: form });

}



// --- Pipeline ---

export async function getModules(): Promise<GenomicsModule[]> {
  return request<GenomicsModule[]>(`${API_BASE}/pipeline/modules`);
}

export async function getPipelineJobs(): Promise<PipelineJob[]> {

  return request<PipelineJob[]>(`${API_BASE}/pipeline/jobs`);

}



export async function getPipelineJob(jobId: string): Promise<PipelineJob> {

  return request<PipelineJob>(`${API_BASE}/pipeline/jobs/${jobId}`);

}



export async function startPipeline(
  sampleId: string,
  sync = true,
  options?: { module?: string; paired_sample_id?: string },
): Promise<PipelineJob> {
  return request<PipelineJob>(`${API_BASE}/pipeline/run?sync=${sync}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sample_id: sampleId,
      module: options?.module,
      paired_sample_id: options?.paired_sample_id,
    }),
  });
}



// --- Reports ---

export async function getReports(): Promise<Report[]> {

  return request<Report[]>(`${API_BASE}/reports/`);

}



export async function getReport(reportId: string): Promise<Report> {

  return request<Report>(`${API_BASE}/reports/${reportId}`);

}



export async function approveReport(reportId: string, notes?: string): Promise<Report> {

  return request<Report>(`${API_BASE}/reports/${reportId}/approve`, {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify({ clinician_notes: notes ?? null }),

  });

}

export async function getReviewQueue(): Promise<import("./types").ReviewQueueItem[]> {
  return request(`${API_BASE}/reports/review-queue`);
}

export async function getPendingVariants(reportId: string): Promise<import("./types").PendingVariantItem[]> {
  return request(`${API_BASE}/reports/${reportId}/pending-variants`);
}

export async function reviewVariant(
  reportId: string,
  annotationId: string,
  action: "approved" | "rejected",
  notes?: string
): Promise<import("./types").PendingVariantItem> {
  return request(`${API_BASE}/reports/${reportId}/variants/${annotationId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, notes: notes ?? null }),
  });
}

export async function downloadReportPdf(reportId: string): Promise<Blob> {
  const headers: HeadersInit = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  const res = await fetch(`${API_BASE}/reports/${reportId}/pdf`, { headers });
  if (!res.ok) {
    throw new ApiClientError("خطا در دریافت PDF", res.status);
  }
  return res.blob();
}



export async function getPatientVariants(patientId: string): Promise<Variant[]> {

  return request<Variant[]>(`${API_BASE}/reports/patient/${patientId}/variants`);

}



export async function exportEhr(patientId: string): Promise<unknown> {

  return request(`${API_BASE}/ehr/export/${patientId}`);

}

export async function exportEhrFhir(patientId: string): Promise<Blob> {
  const headers: HeadersInit = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  const res = await fetch(`${API_BASE}/ehr/export/${patientId}/fhir`, { headers });
  if (!res.ok) throw new ApiClientError("خطا در خروجی FHIR", res.status);
  return res.blob();
}

export async function exportEhrHl7(patientId: string): Promise<Blob> {
  const headers: HeadersInit = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  const res = await fetch(`${API_BASE}/ehr/export/${patientId}/hl7`, { headers });
  if (!res.ok) throw new ApiClientError("خطا در خروجی HL7", res.status);
  return res.blob();
}

export async function getEhrConnectors(): Promise<
  { name: string; display_name: string; display_name_fa: string; supported_formats: string[] }[]
> {
  return request(`${API_BASE}/ehr/connectors`);
}

export async function pushEhr(
  patientId: string,
  connector: "tajhiz" | "sepas",
  format: "fhir" | "hl7" | "json" = "fhir"
): Promise<{ success: boolean; message: string; external_id?: string }> {
  return request(`${API_BASE}/ehr/push/${patientId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connector, format }),
  });
}



// --- AI Decision Support ---

export async function getPlainSummary(reportId: string): Promise<PlainSummary> {
  return request<PlainSummary>(`${API_BASE}/ai/reports/${reportId}/plain-summary`, {
    method: "POST",
  });
}

export async function askVariant(question: string, rsId: string): Promise<VariantAskResult> {
  return request<VariantAskResult>(`${API_BASE}/ai/variants/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, rs_id: rsId }),
  });
}

// --- Variants ---

export async function getVariants(): Promise<Variant[]> {

  return request<Variant[]>(`${API_BASE}/variants/`);

}



// --- Audit ---

export async function getAuditLogs(): Promise<AuditLog[]> {

  return request<AuditLog[]>(`${API_BASE}/audit/logs`);

}



export { ApiClientError };



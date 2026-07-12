import type { DashboardStats, Patient } from "./mockData";
import { mockStats, mockPatients } from "./mockData";

const API_BASE = "/api/v1";

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getHealth(): Promise<boolean> {
  const data = await fetchJson<{ status: string }>(`${API_BASE}/health`);
  return data?.status === "healthy";
}

export async function getPatients(): Promise<Patient[]> {
  const data = await fetchJson<Patient[]>(`${API_BASE}/patients/`);
  return data ?? mockPatients;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const health = await getHealth();
  if (!health) return mockStats;

  const patients = await getPatients();
  return {
    ...mockStats,
    totalPatients: patients.length || mockStats.totalPatients,
  };
}

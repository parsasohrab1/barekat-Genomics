import { Users, FlaskConical, GitBranch, FileText, Dna, Pill } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { useEffect, useState } from "react";
import { getDashboardStats, getPipelineJobs, getReports } from "../lib/api";
import { formatDateTime, jobStatusLabel, stageLabel } from "../lib/format";
import type { DashboardStats } from "../lib/types";
import { monthlyData, variantTypeData } from "../lib/mockData";

function StatCard({
  title, value, icon: Icon, color,
}: {
  title: string; value: string | number; icon: React.ElementType; color: string;
}) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{value}</p>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<
    { id: string; title: string; description: string; time: string; status: string }[]
  >([]);
  const [apiOnline, setApiOnline] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setApiOnline(false));

    Promise.all([getPipelineJobs(), getReports()])
      .then(([jobs, reports]) => {
        const jobActs = jobs.slice(0, 3).map((j) => ({
          id: j.id,
          title: `پایپ‌لاین ${j.sample_label ?? j.id.slice(0, 8)}`,
          description: `${stageLabel[j.stage] ?? j.stage} — ${jobStatusLabel[j.status] ?? j.status}`,
          time: formatDateTime(j.created_at),
          status: j.status === "completed" ? "success" : j.status === "failed" ? "failed" : "running",
        }));
        const reportActs = reports.slice(0, 2).map((r) => ({
          id: r.id,
          title: `گزارش ${r.report_type}`,
          description: r.summary ?? "—",
          time: formatDateTime(r.created_at),
          status: r.status === "completed" ? "success" : "pending",
        }));
        setActivities([...jobActs, ...reportActs]);
      })
      .catch(() => {});
  }, []);

  const s = stats ?? {
    total_patients: 0, total_samples: 0, active_pipelines: 0,
    completed_reports: 0, variants_detected: 0, drug_recommendations: 0,
  };

  const statusBadge: Record<string, string> = {
    success: "badge-success", running: "badge-info",
    pending: "badge-warning", failed: "badge-danger",
  };

  return (
    <div className="space-y-6">
      {!apiOnline && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
          API در دسترس نیست — آمار صفر نمایش داده می‌شود
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <StatCard title="بیماران" value={s.total_patients} icon={Users} color="bg-brand-600" />
        <StatCard title="نمونه‌ها" value={s.total_samples} icon={FlaskConical} color="bg-indigo-500" />
        <StatCard title="پایپ‌لاین فعال" value={s.active_pipelines} icon={GitBranch} color="bg-violet-500" />
        <StatCard title="گزارش‌ها" value={s.completed_reports} icon={FileText} color="bg-emerald-500" />
        <StatCard title="واریانت‌ها" value={s.variants_detected.toLocaleString("fa-IR")} icon={Dna} color="bg-rose-500" />
        <StatCard title="توصیه دارویی" value={s.drug_recommendations} icon={Pill} color="bg-amber-500" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="stat-card lg:col-span-2">
          <h3 className="mb-4 text-sm font-semibold text-slate-700">روند نمونه‌ها و گزارش‌ها</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="samples" name="نمونه" fill="#0891b2" radius={[4, 4, 0, 0]} />
              <Bar dataKey="reports" name="گزارش" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="stat-card">
          <h3 className="mb-4 text-sm font-semibold text-slate-700">توزیع نوع واریانت</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={variantTypeData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={4} dataKey="value">
                {variantTypeData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="stat-card">
        <h3 className="mb-4 text-sm font-semibold text-slate-700">فعالیت‌های اخیر (از API)</h3>
        {activities.length === 0 ? (
          <p className="text-sm text-slate-400">فعالیتی ثبت نشده</p>
        ) : (
          <div className="space-y-3">
            {activities.map((item) => (
              <div key={item.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3 hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-brand-500" />
                  <div>
                    <p className="text-sm font-medium text-slate-700">{item.title}</p>
                    <p className="text-xs text-slate-400">{item.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={statusBadge[item.status] ?? "badge-info"}>{item.status}</span>
                  <span className="text-xs text-slate-400">{item.time}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

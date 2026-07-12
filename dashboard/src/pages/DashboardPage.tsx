import { Users, FlaskConical, GitBranch, FileText, Dna, Pill } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useEffect, useState } from "react";
import { getDashboardStats } from "../lib/api";
import type { DashboardStats } from "../lib/mockData";
import { mockActivities, monthlyData, variantTypeData } from "../lib/mockData";

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  subtitle,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  subtitle?: string;
}) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  );
}

const statusBadge = {
  success: "badge-success",
  running: "badge-info",
  pending: "badge-warning",
  failed: "badge-danger",
};

const statusLabel = {
  success: "تکمیل",
  running: "در حال اجرا",
  pending: "در انتظار",
  failed: "خطا",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getDashboardStats().then(setStats);
  }, []);

  const s = stats ?? {
    totalPatients: 0,
    totalSamples: 0,
    activePipelines: 0,
    completedReports: 0,
    variantsDetected: 0,
    drugRecommendations: 0,
  };

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <StatCard title="بیماران" value={s.totalPatients} icon={Users} color="bg-brand-600" />
        <StatCard title="نمونه‌ها" value={s.totalSamples} icon={FlaskConical} color="bg-indigo-500" />
        <StatCard title="پایپ‌لاین فعال" value={s.activePipelines} icon={GitBranch} color="bg-violet-500" />
        <StatCard title="گزارش‌ها" value={s.completedReports} icon={FileText} color="bg-emerald-500" />
        <StatCard title="واریانت‌ها" value={s.variantsDetected.toLocaleString("fa-IR")} icon={Dna} color="bg-rose-500" />
        <StatCard title="توصیه دارویی" value={s.drugRecommendations} icon={Pill} color="bg-amber-500" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Bar Chart */}
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

        {/* Pie Chart */}
        <div className="stat-card">
          <h3 className="mb-4 text-sm font-semibold text-slate-700">توزیع نوع واریانت</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={variantTypeData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
              >
                {variantTypeData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex justify-center gap-4">
            {variantTypeData.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
                {item.name} ({item.value}%)
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="stat-card">
        <h3 className="mb-4 text-sm font-semibold text-slate-700">فعالیت‌های اخیر</h3>
        <div className="space-y-3">
          {mockActivities.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3 transition-colors hover:bg-slate-50"
            >
              <div className="flex items-center gap-3">
                <div className="h-2 w-2 rounded-full bg-brand-500" />
                <div>
                  <p className="text-sm font-medium text-slate-700">{item.title}</p>
                  <p className="text-xs text-slate-400">{item.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={statusBadge[item.status]}>{statusLabel[item.status]}</span>
                <span className="text-xs text-slate-400">{item.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

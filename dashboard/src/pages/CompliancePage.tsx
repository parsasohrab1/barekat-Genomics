import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";

const API = "/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("barekat_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface Item {
  id: string;
  category: string;
  title_fa: string;
  status: string;
  regulator: string;
  evidence: string;
}

export default function CompliancePage() {
  const [items, setItems] = useState<Item[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});

  useEffect(() => {
    fetch(`${API}/compliance/checklist`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((body) => {
        setItems(body.items || []);
        setSummary(body.summary || {});
      });
  }, []);

  const statusClass: Record<string, string> = {
    implemented: "text-emerald-700",
    partial: "text-amber-700",
    planned: "text-slate-500",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-brand-600" />
        <h1 className="text-lg font-semibold text-slate-800">چک‌لیست انطباق رگولاتوری</h1>
      </div>
      <p className="text-sm text-slate-600">
        پیاده‌سازی‌شده: {summary.implemented ?? 0} · جزئی: {summary.partial ?? 0} · برنامه‌ریزی:{" "}
        {summary.planned ?? 0} · کل: {summary.total ?? 0}
      </p>
      <div className="overflow-x-auto stat-card">
        <table className="data-table">
          <thead>
            <tr>
              <th>عنوان</th>
              <th>دسته</th>
              <th>وضعیت</th>
              <th>مرجع</th>
              <th>شواهد</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td className="text-sm text-slate-800">{i.title_fa}</td>
                <td className="text-xs">{i.category}</td>
                <td className={`text-xs font-medium ${statusClass[i.status] || ""}`}>{i.status}</td>
                <td className="text-xs">{i.regulator}</td>
                <td className="text-xs text-slate-500">{i.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

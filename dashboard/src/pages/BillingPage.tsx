import { useEffect, useState } from "react";
import { CreditCard } from "lucide-react";

const API = "/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("barekat_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface Plan {
  code: string;
  name: string;
  name_fa?: string;
  deployment_mode: string;
  price_monthly_usd: number;
  max_users: number;
  max_samples_month: number;
}

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      fetch(`${API}/billing/plans`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/billing/usage`, { headers: authHeaders() }).then((r) => r.json()),
    ])
      .then(([p, u]) => {
        setPlans(p);
        setUsage(u);
      })
      .catch(() => setMessage("Error loading subscription"))
  }, []);

  async function subscribe(code: string) {
    const res = await fetch(`${API}/billing/subscribe`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ plan_code: code, trial_days: 14 }),
    });
    if (!res.ok) {
      setMessage("Plan activation failed");
      return;
    }
    setMessage(`Plan ${code} activated`);
    setUsage(await fetch(`${API}/billing/usage`, { headers: authHeaders() }).then((r) => r.json()));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <CreditCard className="h-5 w-5 text-brand-600" />
        <h1 className="text-lg font-semibold text-slate-800">Subscription plan (SaaS / On-prem)</h1>
      </div>
      {message && <p className="text-sm text-brand-700">{message}</p>}
      {usage && (
        <div className="stat-card text-sm text-slate-600">
          Status: {String(usage.subscription_status)} · Plan: {String(usage.plan_code ?? "—")} ·
          Samples: {String(usage.samples_used)}/{String(usage.samples_limit ?? "∞")} ·
          Seats: {String(usage.seats_used)}/{String(usage.seats_limit ?? "∞")}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((p) => (
          <div key={p.code} className="stat-card space-y-3">
            <h3 className="font-semibold text-slate-800">{p.name_fa || p.name}</h3>
            <p className="text-xs text-slate-500">{p.deployment_mode}</p>
            <p className="text-2xl font-bold text-brand-700">
              {p.price_monthly_usd > 0 ? `$${p.price_monthly_usd}` : "Custom"}
            </p>
            <p className="text-xs text-slate-600">
              Up to {p.max_users} users · {p.max_samples_month} samples/month
            </p>
            <button
              onClick={() => subscribe(p.code)}
              className="rounded-lg bg-brand-600 px-3 py-2 text-sm text-white"
            >
              Activate
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ArrowRight } from "lucide-react";
import { getPatients, getReviewQueue } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { ReviewQueueItem } from "../lib/types";

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [patients, setPatients] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getReviewQueue(), getPatients()])
      .then(([queue, p]) => {
        setItems(queue);
        setPatients(Object.fromEntries(p.map((x) => [x.id, x.external_id])));
      })
      .catch(() => setError("خطا در بارگذاری صف بررسی"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-400">در حال بارگذاری صف...</p>;
  if (error) return <p className="text-sm text-rose-600">{error}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-800">در انتظار تأیید</h2>
          <p className="text-sm text-slate-500">
            گزارش‌هایی با واریانت ML score &gt; 0.7 که نیاز به بررسی ژنتیک‌دان دارند
          </p>
        </div>
        <span className="badge-warning">{items.length} گزارش</span>
      </div>

      {items.length === 0 ? (
        <p className="stat-card text-center text-sm text-slate-400">موردی در صف بررسی نیست</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="stat-card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">
                    بیمار: {patients[item.patient_id] ?? item.patient_id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-slate-400">
                    گزارش {item.id.slice(0, 8)} — {formatDateTime(item.created_at)}
                  </p>
                  {item.variant_summary && (
                    <p className="mt-1 text-xs text-slate-500">
                      {item.variant_summary.high_priority ?? 0} واریانت با ML بالا
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {item.pending_variant_count > 0 && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                      <AlertCircle className="h-3.5 w-3.5" />
                      {item.pending_variant_count} واریانت در انتظار
                    </span>
                  )}
                  <Link
                    to={`/reports/${item.id}`}
                    className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
                  >
                    بررسی
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

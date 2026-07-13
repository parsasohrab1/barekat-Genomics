import { useEffect, useState } from "react";
import { getVariants } from "../lib/api";
import { sigClass, sigLabel } from "../lib/format";
import type { Variant } from "../lib/types";

export default function VariantsPage() {
  const [variants, setVariants] = useState<Variant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getVariants()
      .then(setVariants)
      .catch(() => setError("خطا در بارگذاری واریانت‌ها"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-400">در حال بارگذاری...</p>;
  if (error) return <p className="text-sm text-rose-600">{error}</p>;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-card">
      {variants.length === 0 ? (
        <p className="p-8 text-center text-sm text-slate-400">واریانتی ثبت نشده</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>بیمار</th>
              <th>ژن</th>
              <th>rsID</th>
              <th>موقعیت</th>
              <th>اهمیت بالینی</th>
              <th>اولویت</th>
              <th>دارو</th>
            </tr>
          </thead>
          <tbody>
            {variants.map((v) => {
              const ann = v.annotations[0];
              return (
                <tr key={v.id}>
                  <td>{v.patient_external_id ?? "—"}</td>
                  <td className="font-medium text-brand-700">{ann?.gene ?? "—"}</td>
                  <td className="font-mono text-xs">{v.rs_id ?? "—"}</td>
                  <td className="font-mono text-xs">{v.chromosome}:{v.position}</td>
                  <td>
                    {ann?.clinical_significance ? (
                      <span className={sigClass[ann.clinical_significance] ?? "badge-info"}>
                        {sigLabel[ann.clinical_significance] ?? ann.clinical_significance}
                      </span>
                    ) : "—"}
                  </td>
                  <td>
                    {ann?.priority_score != null && (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-brand-500"
                            style={{ width: `${ann.priority_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500">
                          {(ann.priority_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                  </td>
                  <td>{v.drug ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

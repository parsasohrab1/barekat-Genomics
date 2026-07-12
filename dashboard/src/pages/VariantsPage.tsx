import { mockVariants } from "../lib/mockData";

const sigClass: Record<string, string> = {
  pathogenic: "badge-danger",
  likely_pathogenic: "badge-warning",
  uncertain_significance: "badge-info",
  benign: "badge-success",
};

const sigLabel: Record<string, string> = {
  pathogenic: "بیماری‌زا",
  likely_pathogenic: "احتمال بیماری‌زا",
  uncertain_significance: "نامشخص",
  benign: "خنثی",
};

export default function VariantsPage() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-card">
      <table className="data-table">
        <thead>
          <tr>
            <th>ژن</th>
            <th>rsID</th>
            <th>موقعیت</th>
            <th>اهمیت بالینی</th>
            <th>اولویت</th>
            <th>دارو مرتبط</th>
          </tr>
        </thead>
        <tbody>
          {mockVariants.map((v) => (
            <tr key={v.id}>
              <td className="font-medium text-brand-700">{v.gene}</td>
              <td className="font-mono text-xs">{v.rs_id}</td>
              <td className="font-mono text-xs">{v.chromosome}:{v.position.toLocaleString("fa-IR")}</td>
              <td><span className={sigClass[v.clinical_significance]}>{sigLabel[v.clinical_significance]}</span></td>
              <td>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-brand-500" style={{ width: `${v.priority_score * 100}%` }} />
                  </div>
                  <span className="text-xs text-slate-500">{(v.priority_score * 100).toFixed(0)}%</span>
                </div>
              </td>
              <td>{v.drug}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

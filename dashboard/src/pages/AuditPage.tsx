import { useEffect, useState } from "react";
import { getAuditLogs } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { AuditLog } from "../lib/types";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getAuditLogs()
      .then(setLogs)
      .catch(() => setError("Access to the audit log is not allowed"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-400">Loading...</p>;
  if (error) return <p className="text-sm text-rose-600">{error}</p>;

  return (
    <div className="stat-card">
      <h2 className="mb-4 text-sm font-semibold text-slate-700">Audit log</h2>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Resource</th>
              <th>ID</th>
              <th>User</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="text-xs">{formatDateTime(log.created_at)}</td>
                <td>{log.action}</td>
                <td>{log.resource_type}</td>
                <td className="font-mono text-xs">{log.resource_id ?? "—"}</td>
                <td className="font-mono text-xs">{log.user_id ?? "—"}</td>
                <td className="text-xs">{log.ip_address ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

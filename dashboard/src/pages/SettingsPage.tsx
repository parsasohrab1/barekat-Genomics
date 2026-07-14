import { useEffect, useState } from "react";
import { Shield, Database, Cpu, Globe, Activity, AlertCircle } from "lucide-react";

import { getPlatformSettings, ApiClientError } from "../lib/api";
import type { PlatformSettings } from "../lib/types";

export default function SettingsPage() {
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getPlatformSettings();
        if (!cancelled) {
          setSettings(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiClientError ? err.message : "خطا در دریافت تنظیمات");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500">در حال بارگذاری تنظیمات...</p>;
  }

  if (error || !settings) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-medium">تنظیمات در دسترس نیست</p>
          <p className="mt-1">{error ?? "فقط نقش مدیر می‌تواند تنظیمات HIPAA را ببیند."}</p>
        </div>
      </div>
    );
  }

  const cards = [
    {
      icon: Shield,
      title: "امنیت و HIPAA",
      desc: `رمزنگاری PHI · ممیزی ${settings.audit_log_enabled ? "فعال" : "غیرفعال"} · نگهداری ${settings.phi_retention_days} روز`,
      enabled: settings.audit_log_enabled,
    },
    {
      icon: Database,
      title: "پایگاه داده مرجع",
      desc: `${settings.genome_build} · اسکمای گزارش v${settings.clinical_report_schema_version}`,
      enabled: true,
    },
    {
      icon: Cpu,
      title: "مدل ML",
      desc: `${settings.variant_classifier_model} · A/B test ${settings.ml_ab_test_enabled ? "فعال" : "غیرفعال"}`,
      enabled: true,
    },
    {
      icon: Globe,
      title: "اتصال EHR",
      desc: `FHIR org: ${settings.ehr_fhir_organization_id} · HL7: ${settings.ehr_hl7_sending_facility}`,
      enabled: true,
    },
    {
      icon: Activity,
      title: "پایپ‌لاین و محیط",
      desc: `محیط ${settings.app_env} · حالت ${settings.pipeline_mode} · backend ${settings.pipeline_backend}`,
      enabled: settings.pipeline_mode === "production" || settings.app_env !== "production",
    },
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        مقادیر از پیکربندی سرور خوانده می‌شوند. تغییر دائمی از طریق متغیرهای محیطی و راه‌اندازی مجدد انجام می‌شود.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {cards.map(({ icon: Icon, title, desc, enabled }) => (
          <div key={title} className="stat-card">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
                <Icon className="h-5 w-5 text-slate-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-slate-700">{title}</p>
                  <span className={enabled ? "badge-success" : "badge-warning"}>
                    {enabled ? "فعال" : "غیرفعال"}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

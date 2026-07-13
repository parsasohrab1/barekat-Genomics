import { Shield, Database, Cpu, Globe } from "lucide-react";

const settings = [
  { icon: Shield, title: "امنیت و HIPAA", desc: "رمزنگاری PHI، لاگ ممیزی، نگهداری ۷ ساله", enabled: true },
  { icon: Database, title: "پایگاه داده مرجع", desc: "GRCh38 — dbSNP، ClinVar، PharmGKB", enabled: true },
  { icon: Cpu, title: "مدل ML", desc: "XGBoost+RF ensemble — نسخه‌بندی و A/B test", enabled: true },
  {
    icon: Globe,
    title: "اتصال EHR",
    desc: "FHIR R4 (Observation, DiagnosticReport, MedicationRequest) · HL7 v2 ORU · تجهیز · سپاس",
    enabled: true,
  },
];

export default function SettingsPage() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {settings.map(({ icon: Icon, title, desc, enabled }) => (
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
  );
}

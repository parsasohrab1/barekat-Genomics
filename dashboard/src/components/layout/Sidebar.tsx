import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  FlaskConical,
  GitBranch,
  FileText,
  Dna,
  Settings,
  ChevronLeft,
  Activity,
  ScrollText,
  ClipboardCheck,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "داشبورد", roles: ["physician", "clinician", "analyst", "geneticist", "lab_tech", "admin"] },
  { to: "/patients", icon: Users, label: "بیماران", roles: ["physician", "clinician", "analyst", "geneticist", "lab_tech", "admin"] },
  { to: "/samples", icon: FlaskConical, label: "نمونه‌ها", roles: ["lab_tech", "admin"] },
  { to: "/pipeline", icon: GitBranch, label: "پایپ‌لاین", roles: ["lab_tech", "admin"] },
  { to: "/reports", icon: FileText, label: "گزارش‌ها", roles: ["physician", "clinician", "analyst", "geneticist", "admin"] },
  { to: "/review", icon: ClipboardCheck, label: "در انتظار تأیید", roles: ["analyst", "geneticist", "admin"] },
  { to: "/variants", icon: Dna, label: "واریانت‌ها", roles: ["physician", "clinician", "analyst", "geneticist", "admin"] },
  { to: "/billing", icon: Activity, label: "اشتراک", roles: ["admin"] },
  { to: "/compliance", icon: ScrollText, label: "انطباق", roles: ["admin", "analyst", "geneticist"] },
  { to: "/audit", icon: ScrollText, label: "ممیزی", roles: ["admin"] },
  { to: "/settings", icon: Settings, label: "تنظیمات", roles: ["admin"] },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user } = useAuth();
  const visibleItems = navItems.filter((item) => user && item.roles.includes(user.role));

  return (
    <aside
      className={`fixed top-0 right-0 z-40 flex h-screen flex-col bg-sidebar text-slate-300 transition-all duration-300 ${
        collapsed ? "w-[72px]" : "w-64"
      }`}
    >
      <div className="flex h-16 items-center gap-3 border-b border-slate-700/50 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-600">
          <Activity className="h-5 w-5 text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="truncate text-sm font-bold text-white">barekat Genomics</p>
            <p className="truncate text-[10px] text-slate-400">پلتفرم ژنومیکس</p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {visibleItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? "bg-sidebar-active text-white shadow-sm"
                  : "text-slate-400 hover:bg-sidebar-hover hover:text-white"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-700/50 p-3">
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-sidebar-hover hover:text-white"
          aria-label="جمع کردن سایدبار"
        >
          <ChevronLeft
            className={`h-4 w-4 transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`}
          />
          {!collapsed && <span>جمع کردن</span>}
        </button>
      </div>
    </aside>
  );
}

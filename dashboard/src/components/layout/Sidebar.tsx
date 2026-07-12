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
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "داشبورد" },
  { to: "/patients", icon: Users, label: "بیماران" },
  { to: "/samples", icon: FlaskConical, label: "نمونه‌ها" },
  { to: "/pipeline", icon: GitBranch, label: "پایپ‌لاین" },
  { to: "/reports", icon: FileText, label: "گزارش‌ها" },
  { to: "/variants", icon: Dna, label: "واریانت‌ها" },
  { to: "/settings", icon: Settings, label: "تنظیمات" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={`fixed top-0 right-0 z-40 flex h-screen flex-col bg-sidebar text-slate-300 transition-all duration-300 ${
        collapsed ? "w-[72px]" : "w-64"
      }`}
    >
      {/* Logo */}
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

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map(({ to, icon: Icon, label }) => (
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

      {/* Collapse toggle */}
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

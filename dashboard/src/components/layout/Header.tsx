import { useLocation } from "react-router-dom";

import { Bell, Search, Menu, User, LogOut } from "lucide-react";

import { useAuth, ROLE_LABELS } from "../../context/AuthContext";



const pageTitles: Record<string, string> = {

  "/": "داشبورد",

  "/patients": "بیماران",

  "/samples": "نمونه‌ها",

  "/pipeline": "پایپ‌لاین پردازش",

  "/reports": "گزارش‌های ژنومی",

  "/variants": "واریانت‌ها",

  "/settings": "تنظیمات",

  "/audit": "لاگ ممیزی",

};



interface HeaderProps {

  onMenuClick: () => void;

}



export default function Header({ onMenuClick }: HeaderProps) {

  const location = useLocation();

  const { user, logout } = useAuth();

  const title =

    location.pathname.startsWith("/reports/") && location.pathname !== "/reports"

      ? "جزئیات گزارش"

      : (pageTitles[location.pathname] ?? "داشبورد");



  return (

    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-header">

      <div className="flex items-center gap-4">

        <button

          onClick={onMenuClick}

          className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 lg:hidden"

          aria-label="منو"

        >

          <Menu className="h-5 w-5" />

        </button>

        <div>

          <h1 className="text-lg font-bold text-slate-800">{title}</h1>

          <p className="text-xs text-slate-400">barekat Genomics Platform</p>

        </div>

      </div>



      <div className="flex items-center gap-3">

        <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 md:flex">

          <Search className="h-4 w-4 text-slate-400" />

          <input

            type="text"

            placeholder="جستجوی بیمار، نمونه، واریانت..."

            className="w-56 bg-transparent text-sm outline-none placeholder:text-slate-400"

          />

        </div>



        <button className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100">

          <Bell className="h-5 w-5" />

          <span className="absolute left-1.5 top-1.5 h-2 w-2 rounded-full bg-rose-500" />

        </button>



        <div className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5">

          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-brand-700">

            <User className="h-4 w-4" />

          </div>

          <div className="hidden text-right sm:block">

            <p className="text-sm font-medium text-slate-700">{user?.full_name ?? "—"}</p>

            <p className="text-[10px] text-slate-400">

              {user ? ROLE_LABELS[user.role] ?? user.role : ""}

            </p>

          </div>

          <button

            onClick={logout}

            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-rose-600"

            title="خروج"

          >

            <LogOut className="h-4 w-4" />

          </button>

        </div>

      </div>

    </header>

  );

}


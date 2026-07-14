import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMe, login as apiLogin, setAuthToken } from "../lib/api";
import type { User } from "../lib/types";

const TOKEN_KEY = "barekat_token";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: string[]) => boolean;
  canAccess: (path: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const ROLE_PATHS: Record<string, string[]> = {
  physician: ["/", "/patients", "/reports", "/variants"],
  clinician: ["/", "/patients", "/reports", "/variants"],
  analyst: ["/", "/patients", "/reports", "/review", "/variants"],
  geneticist: ["/", "/patients", "/reports", "/review", "/variants"],
  lab_tech: ["/", "/patients", "/samples", "/pipeline"],
  admin: [
    "/",
    "/patients",
    "/samples",
    "/pipeline",
    "/reports",
    "/review",
    "/variants",
    "/settings",
    "/audit",
    "/billing",
    "/compliance",
  ],
};

function pathAllowed(role: string, path: string): boolean {
  const allowed = ROLE_PATHS[role] ?? [];
  if (path.startsWith("/reports/") && path !== "/reports") {
    return allowed.includes("/reports");
  }
  return allowed.some((p) => (p === "/" ? path === "/" : path.startsWith(p)));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setAuthToken(null);
  }, []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    setAuthToken(token);
    getMe()
      .then(setUser)
      .catch(() => logout())
      .finally(() => setLoading(false));
  }, [token, logout]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const hasRole = useCallback(
    (...roles: string[]) => (user ? roles.includes(user.role) : false),
    [user]
  );

  const canAccess = useCallback(
    (path: string) => (user ? pathAllowed(user.role, path) : false),
    [user]
  );

  const value = useMemo(
    () => ({ user, token, loading, login, logout, hasRole, canAccess }),
    [user, token, loading, login, logout, hasRole, canAccess]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export const ROLE_LABELS: Record<string, string> = {
  clinician: "پزشک",
  geneticist: "ژنتیک‌دان",
  lab_tech: "تکنسین آزمایشگاه",
  admin: "مدیر سیستم",
};

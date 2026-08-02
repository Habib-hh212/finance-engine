import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { TOKEN_STORAGE_KEY } from "../api/client";
import { login as apiLogin, me as apiMe, register as apiRegister, type CurrentUser } from "../api/auth";

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = async () => {
    if (!localStorage.getItem(TOKEN_STORAGE_KEY)) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await apiMe());
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token } = await apiLogin(email, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
    setUser(await apiMe());
  };

  const register = async (email: string, password: string, name: string) => {
    const { access_token } = await apiRegister(email, password, name);
    localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
    setUser(await apiMe());
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { listCompanies } from "../api/companies";
import type { Company } from "../api/types";

const STORAGE_KEY = "finance-engine.selectedCompanyId";

interface CompanyContextValue {
  companies: Company[];
  company: Company | null;
  loading: boolean;
  error: string | null;
  selectCompany: (id: string) => void;
  refresh: () => Promise<void>;
}

const CompanyContext = createContext<CompanyContextValue | undefined>(undefined);

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(localStorage.getItem(STORAGE_KEY));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listCompanies();
      setCompanies(list);
      if (list.length > 0 && !list.some((c) => c.id === selectedId)) {
        setSelectedId(list[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach the API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectCompany = (id: string) => {
    setSelectedId(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  const company = companies.find((c) => c.id === selectedId) ?? null;

  return (
    <CompanyContext.Provider value={{ companies, company, loading, error, selectCompany, refresh: load }}>
      {children}
    </CompanyContext.Provider>
  );
}

export function useCompany() {
  const ctx = useContext(CompanyContext);
  if (!ctx) throw new Error("useCompany must be used within a CompanyProvider");
  return ctx;
}

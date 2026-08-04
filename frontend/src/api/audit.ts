import { apiGet } from "./client";
import type { AuditLogEntry } from "./types";

export const getAuditLog = (companyId: string, entityType?: string) =>
  apiGet<AuditLogEntry[]>(`/audit-log?company_id=${companyId}${entityType ? `&entity_type=${entityType}` : ""}`);

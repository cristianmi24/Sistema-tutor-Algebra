import { z } from "zod";

import { userSummarySchema } from "@/features/auth/api";
import { request } from "@/lib/api";

export const institutionSchema = z.object({
  id: z.string(),
  code: z.string(),
  name: z.string(),
  country: z.string().nullable(),
  city: z.string().nullable(),
  consent_policy: z.record(z.string(), z.unknown()),
  retention_days: z.number().nullable(),
  is_active: z.boolean(),
});
export type Institution = z.infer<typeof institutionSchema>;

export const auditLogSchema = z.object({
  id: z.string(),
  occurred_at: z.string(),
  actor_user_id: z.string().nullable(),
  actor_role: z.string().nullable(),
  action: z.string(),
  resource_type: z.string().nullable(),
  resource_id: z.string().nullable(),
  outcome: z.string(),
  request_id: z.string().nullable(),
  details: z.record(z.string(), z.unknown()),
});
export type AuditLog = z.infer<typeof auditLogSchema>;

export function pageSchema<T extends z.ZodType>(item: T) {
  return z.object({ items: z.array(item), page: z.number(), page_size: z.number(), total: z.number() });
}

export interface StaffUserCreate {
  email: string;
  password: string;
  role: "TEACHER" | "RESEARCHER" | "ADMIN";
  institution_code?: string;
  group_assignments: { grade: "7" | "8" | "9"; group_code: string }[];
}

export interface InstitutionIn {
  code: string;
  name: string;
  country?: string;
  city?: string;
  consent_policy: { required_parties: string[] };
  retention_days?: number;
}

function qs(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()}` : "";
}

export const adminApi = {
  users: (params: { role?: string | undefined; page?: number | undefined; page_size?: number | undefined }) => request(`/admin/users${qs(params)}`, pageSchema(userSummarySchema)),
  createUser: (payload: StaffUserCreate) => request("/admin/users", userSummarySchema, { method: "POST", body: payload }),
  setUserStatus: (userId: string, status: "ACTIVE" | "DISABLED") =>
    request(`/admin/users/${userId}/status`, userSummarySchema, { method: "PATCH", body: { status } }),
  institutions: () => request("/admin/institutions", z.array(institutionSchema)),
  createInstitution: (payload: InstitutionIn) => request("/admin/institutions", institutionSchema, { method: "POST", body: payload }),
  audit: (params: { action?: string | undefined; page?: number | undefined; page_size?: number | undefined }) => request(`/admin/audit${qs(params)}`, pageSchema(auditLogSchema)),
};

export const adminQueryKeys = {
  users: (params: object) => ["admin", "users", params] as const,
  institutions: ["admin", "institutions"] as const,
  audit: (params: object) => ["admin", "audit", params] as const,
};

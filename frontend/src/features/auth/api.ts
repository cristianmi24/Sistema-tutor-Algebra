import { z } from "zod";

import { request, roleSchema } from "@/lib/api";

export const userSummarySchema = z.object({
  id: z.string(),
  role: roleSchema,
  status: z.enum(["ACTIVE", "PENDING_CONSENT", "LOCKED", "DISABLED"]),
  display_code: z.string(),
  institution_id: z.string().nullable(),
  email: z.string().nullable().optional(),
  username: z.string().nullable().optional(),
  grade: z.string().nullable().optional(),
  group_code: z.string().nullable().optional(),
  research_status: z.string().nullable().optional(),
});
export type UserSummary = z.infer<typeof userSummarySchema>;

export const tokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.literal("bearer"),
  expires_in: z.number(),
  user: userSummarySchema,
});
export type TokenResponse = z.infer<typeof tokenResponseSchema>;

export const legalDocumentSchema = z.object({
  kind: z.enum(["PRIVACY_POLICY", "TERMS"]),
  version: z.string(),
  locale: z.string(),
  title: z.string(),
  body_markdown: z.string(),
  published_at: z.string().nullable(),
});
export type LegalDocument = z.infer<typeof legalDocumentSchema>;

export const institutionPublicSchema = z.object({
  code: z.string(),
  name: z.string(),
  required_consent_parties: z.array(z.string()),
});
export type InstitutionPublic = z.infer<typeof institutionPublicSchema>;

export const consentSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  consent_party: z.enum(["STUDENT", "GUARDIAN", "INSTITUTION", "RESEARCHER"]),
  consent_status: z.enum(["PENDING", "ACCEPTED", "DECLINED", "REVOKED"]),
  privacy_policy_version: z.string(),
  terms_version: z.string(),
  accepted_at: z.string().nullable(),
  revoked_at: z.string().nullable(),
  created_at: z.string(),
});
export type Consent = z.infer<typeof consentSchema>;

export interface RegisterPayload {
  identifier: string;
  password: string;
  institution_code: string;
  grade: "7" | "8" | "9";
  group_code?: string;
  birth_year?: number;
  consents: { party: "STUDENT" | "GUARDIAN"; privacy_policy_version: string; terms_version: string; status: "ACCEPTED"; guardian_reference?: string }[];
}

export const registerResponseSchema = z.object({
  user_id: z.string(),
  participant_code: z.string(),
  status: z.string(),
  research_status: z.string(),
});

const empty = z.undefined().or(z.unknown());

export const authApi = {
  login: (identifier: string, password: string) =>
    request("/auth/login", tokenResponseSchema, { method: "POST", body: { identifier, password } }),
  refresh: () => request("/auth/refresh", tokenResponseSchema, { method: "POST", skipAuthRetry: true }),
  logout: () => request("/auth/logout", empty, { method: "POST" }),
  me: () => request("/auth/me", userSummarySchema),
  register: (payload: RegisterPayload) => request("/auth/register", registerResponseSchema, { method: "POST", body: payload }),
  forgotPassword: (email: string) =>
    request("/auth/forgot-password", z.object({ message: z.string() }), { method: "POST", body: { email } }),
  resetPassword: (token: string, newPassword: string) =>
    request("/auth/reset-password", empty, { method: "POST", body: { token, new_password: newPassword } }),
  legalDocuments: () => request("/legal/documents", z.array(legalDocumentSchema)),
  institutions: () => request("/legal/institutions", z.array(institutionPublicSchema)),
  myConsents: () => request("/consents/me", z.array(consentSchema)),
  recordGuardianConsent: (userId: string, versions: { privacy_policy_version: string; terms_version: string }, guardianReference: string) =>
    request("/consents", consentSchema, {
      method: "POST",
      body: { user_id: userId, consent: { party: "GUARDIAN", ...versions, status: "ACCEPTED", guardian_reference: guardianReference } },
    }),
};

export const authQueryKeys = {
  legalDocuments: ["legal", "documents"] as const,
  institutions: ["legal", "institutions"] as const,
  myConsents: ["consents", "me"] as const,
};

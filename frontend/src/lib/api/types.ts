import { z } from "zod";

/** Sobre de error estándar del backend (ver docs/08-api.md). */
export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().nullable(),
    details: z.unknown().nullable(),
  }),
});

export const healthSchema = z.object({
  status: z.literal("ok"),
  service: z.string(),
  version: z.string(),
  environment: z.string(),
});
export type Health = z.infer<typeof healthSchema>;

export const readinessSchema = z.object({
  status: z.literal("ready"),
  database: z.literal("ok"),
});
export type Readiness = z.infer<typeof readinessSchema>;

export const roleSchema = z.enum(["STUDENT", "TEACHER", "RESEARCHER", "ADMIN"]);
export type Role = z.infer<typeof roleSchema>;

export const metaSchema = z.object({
  roles: z.array(roleSchema),
  student_states: z.array(z.string()),
  student_state_labels: z.record(z.string(), z.string()),
  intervention_levels: z.array(z.string()),
  task_types: z.array(z.string()),
  worked_example_types: z.array(z.string()),
  representations: z.array(z.string()),
  scaffold_types: z.array(z.string()),
  interaction_event_types: z.array(z.string()),
  grades: z.array(z.string()),
  privacy_policy_version: z.string(),
  terms_version: z.string(),
  llm_enabled: z.boolean(),
});
export type Meta = z.infer<typeof metaSchema>;

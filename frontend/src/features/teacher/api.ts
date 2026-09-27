import { z } from "zod";

import { request } from "@/lib/api";

export const studentOverviewSchema = z.object({
  student_id: z.string(),
  participant_code: z.string(),
  grade: z.string(),
  group_code: z.string().nullable(),
  account_status: z.string(),
  active_session_id: z.string().nullable(),
  current_task_code: z.string().nullable(),
  current_task_title: z.string().nullable(),
  last_event_at: z.string().nullable(),
  last_event_type: z.string().nullable(),
  system_helps_in_session: z.number(),
  help_requests_in_session: z.number(),
  teacher_interventions_in_session: z.number(),
  state_label: z.string().nullable(),
  operational_state: z.string().nullable(),
  suggest_teacher: z.boolean(),
});
export type StudentOverview = z.infer<typeof studentOverviewSchema>;

export const groupSchema = z.object({ institution_id: z.string(), grade: z.string(), group_code: z.string(), students: z.array(studentOverviewSchema) });
export type Group = z.infer<typeof groupSchema>;

export const interventionSchema = z.object({
  id: z.string(),
  teacher_code: z.string().nullable(),
  student_id: z.string(),
  participant_code: z.string().nullable(),
  session_id: z.string(),
  task_id: z.string().nullable(),
  interaction_id: z.string().nullable(),
  intervention_type: z.string(),
  content: z.string(),
  visibility: z.enum(["STUDENT", "RESEARCH_ONLY"]),
  student_seen_at: z.string().nullable(),
  created_at: z.string(),
  source: z.literal("TEACHER"),
});
export type Intervention = z.infer<typeof interventionSchema>;

export const studentMessageSchema = z.object({
  id: z.string(),
  task_id: z.string().nullable(),
  intervention_type: z.string(),
  content: z.string(),
  created_at: z.string(),
  seen: z.boolean(),
});
export type StudentMessage = z.infer<typeof studentMessageSchema>;

export type InterventionType = "QUESTION" | "COMMENT" | "OBSERVATION" | "REDIRECTION" | "ENCOURAGEMENT";

export interface InterventionIn {
  session_id: string;
  task_id?: string;
  intervention_type: InterventionType;
  content: string;
  visibility: "STUDENT" | "RESEARCH_ONLY";
}

export const INTERVENTION_LABEL: Record<InterventionType, string> = {
  QUESTION: "Pregunta",
  COMMENT: "Comentario",
  OBSERVATION: "Observación",
  REDIRECTION: "Reorientación",
  ENCOURAGEMENT: "Ánimo",
};

export const teacherApi = {
  groups: () => request("/teacher/groups", z.array(groupSchema)),
  interventions: (sessionId: string) => request(`/teacher/interventions?session_id=${sessionId}`, z.array(interventionSchema)),
  createIntervention: (payload: InterventionIn) => request("/teacher/interventions", interventionSchema, { method: "POST", body: payload }),
  studentMessages: (sessionId: string) => request(`/sessions/${sessionId}/teacher-messages`, z.array(studentMessageSchema)),
  markSeen: (sessionId: string, messageId: string) => request(`/sessions/${sessionId}/teacher-messages/${messageId}/seen`, z.unknown(), { method: "POST" }),
};

export const teacherQueryKeys = {
  groups: ["teacher", "groups"] as const,
  interventions: (sessionId: string) => ["teacher", "interventions", sessionId] as const,
  messages: (sessionId: string) => ["sessions", sessionId, "teacher-messages"] as const,
};

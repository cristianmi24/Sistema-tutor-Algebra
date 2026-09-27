import { z } from "zod";

import { request } from "@/lib/api";

export const representationSchema = z.enum(["VERBAL", "NUMERIC", "TABULAR", "GRAPHIC", "SYMBOLIC"]);
export type Representation = z.infer<typeof representationSchema>;

export const taskTypeSchema = z.enum(["NUMERIC_PATTERN", "FIGURAL_PATTERN", "TABLE", "GRAPH", "SYMBOLIC", "JUSTIFICATION", "TRANSFER"]);
export type TaskType = z.infer<typeof taskTypeSchema>;

export const questionSchema = z.object({
  id: z.string(),
  kind: z.enum(["predict", "explain", "describe", "generalize", "table", "justify", "compare", "transfer_predict"]),
  text: z.string(),
  position: z.number().optional(),
  positions: z.array(z.number()).optional(),
  representations: z.array(representationSchema).optional(),
});
export type Question = z.infer<typeof questionSchema>;

export const patternSchema = z.object({
  kind: z.enum(["numeric", "figural", "table", "graph", "situation"]),
  terms: z.array(z.number()).optional(),
  shape: z.string().optional(),
  expression: z.string().optional(),
  shown_figures: z.array(z.number()).optional(),
  positions: z.array(z.number()).optional(),
  known: z.record(z.string(), z.number()).optional(),
  x_label: z.string().optional(),
  y_label: z.string().optional(),
  x_max: z.number().optional(),
  y_max: z.number().optional(),
});
export type Pattern = z.infer<typeof patternSchema>;

export const taskSchema = z.object({
  id: z.string(),
  code: z.string(),
  task_type: taskTypeSchema,
  title: z.string(),
  skill: z.string(),
  difficulty: z.number(),
  grade_min: z.string(),
  grade_max: z.string(),
  statement: z.object({
    prompt: z.string(),
    pattern: patternSchema,
    questions: z.array(questionSchema),
    expected_time_ms: z.number().optional(),
  }),
  related_task_id: z.string().nullable(),
  order_index: z.number(),
});
export type Task = z.infer<typeof taskSchema>;

export const workedExampleSchema = z.object({
  id: z.string(),
  task_id: z.string(),
  example_type: z.enum(["FULL", "PARTIAL", "HIDDEN_STEPS", "SELF_EXPLANATION", "STRATEGY_COMPARISON", "INTENTIONAL_ERROR", "TRANSFER"]),
  title: z.string(),
  content: z.record(z.string(), z.unknown()),
  order_index: z.number(),
});
export type WorkedExample = z.infer<typeof workedExampleSchema>;

export const sessionTaskSchema = z.object({
  id: z.string(),
  task: taskSchema,
  order_index: z.number(),
  status: z.enum(["PENDING", "OPEN", "COMPLETED", "ABANDONED"]),
  opened_at: z.string().nullable(),
  completed_at: z.string().nullable(),
});

export const sessionSchema = z.object({
  id: z.string(),
  student_id: z.string(),
  participant_code: z.string().nullable().optional(),
  started_at: z.string(),
  ended_at: z.string().nullable(),
  status: z.enum(["ACTIVE", "COMPLETED", "ABANDONED"]),
  tasks: z.array(sessionTaskSchema),
  context: z.record(z.string(), z.unknown()),
});
export type Session = z.infer<typeof sessionSchema>;

export const sessionSummarySchema = z.object({
  id: z.string(),
  student_id: z.string(),
  participant_code: z.string().nullable().optional(),
  started_at: z.string(),
  ended_at: z.string().nullable(),
  status: z.enum(["ACTIVE", "COMPLETED", "ABANDONED"]),
  task_count: z.number(),
  completed_count: z.number(),
  interaction_count: z.number(),
  help_count: z.number(),
});
export type SessionSummary = z.infer<typeof sessionSummarySchema>;

export const helpOfferSchema = z.object({
  scaffold_event_id: z.string().nullable(),
  offered: z.boolean(),
  level: z.number(),
  scaffold_type: z.string().nullable(),
  text: z.string().nullable(),
  follow_up: z.string().nullable().optional(),
  can_reformulate: z.boolean().optional(),
  message: z.string(),
});
export type HelpOffer = z.infer<typeof helpOfferSchema>;

export const responseOutSchema = z.object({
  id: z.string(),
  task_id: z.string(),
  question_id: z.string(),
  attempt_number: z.number(),
  representation: representationSchema,
  content: z.record(z.string(), z.unknown()),
  is_edit_of: z.string().nullable(),
  submitted_at: z.string(),
  evaluation: z.record(z.string(), z.unknown()).nullable().optional(),
});
export type ResponseOut = z.infer<typeof responseOutSchema>;

export const submitResultSchema = z.object({ response: responseOutSchema, help: helpOfferSchema.nullable(), state_label: z.string() });
export type SubmitResult = z.infer<typeof submitResultSchema>;

export const interactionSchema = z.object({
  id: z.string(),
  session_id: z.string(),
  student_id: z.string(),
  task_id: z.string().nullable(),
  timestamp: z.string(),
  sequence: z.number(),
  event_type: z.string(),
  student_action: z.string().nullable(),
  student_response: z.record(z.string(), z.unknown()).nullable(),
  representation: z.string().nullable(),
  help_requested: z.boolean(),
  help_level: z.number().nullable(),
  help_type: z.string().nullable(),
  help_content: z.string().nullable(),
  help_accepted: z.boolean().nullable(),
  help_rejected: z.boolean().nullable(),
  scaffold_event_id: z.string().nullable(),
  ai_interpretation: z.record(z.string(), z.unknown()).nullable(),
  teacher_intervention_id: z.string().nullable(),
  next_student_action: z.string().nullable(),
  client_meta: z.record(z.string(), z.unknown()),
});
export type Interaction = z.infer<typeof interactionSchema>;

export const scaffoldEventSchema = z.object({
  id: z.string(),
  session_id: z.string(),
  student_id: z.string(),
  task_id: z.string(),
  interaction_id: z.string().nullable(),
  scaffold_id: z.string().nullable(),
  scaffold_code: z.string().nullable(),
  scaffold_type: z.string().nullable(),
  decision: z.record(z.string(), z.unknown()),
  previous_help_level: z.number(),
  current_help_level: z.number(),
  reason_for_change: z.string().nullable(),
  source: z.string(),
  delivered_text: z.string().nullable(),
  accepted: z.boolean().nullable(),
  rejected: z.boolean().nullable(),
  reformulations: z.number(),
  result: z.string(),
  subsequent_strategy: z.string().nullable(),
  created_at: z.string(),
  resolved_at: z.string().nullable(),
});
export type ScaffoldEvent = z.infer<typeof scaffoldEventSchema>;

export interface ClientMeta {
  time_on_task_ms?: number;
  clicks?: number;
  edits?: number;
  device?: string;
}

export type ClientEventType = "TASK_OPENED" | "EXAMPLE_OPENED" | "REPRESENTATION_CHANGED" | "SELF_EXPLANATION" | "TASK_COMPLETED" | "TASK_ABANDONED";

export type ResponseDraftContent = Record<string, unknown>;

export interface ResponsePayload {
  task_id: string;
  question_id: string;
  representation: Representation;
  content: Record<string, unknown>;
  is_edit_of?: string;
  client_meta?: ClientMeta;
}

export const studentApi = {
  tasks: (grade?: string) => request(`/tasks${grade ? `?grade=${grade}` : ""}`, z.array(taskSchema)),
  workedExamples: (taskId: string) => request(`/tasks/${taskId}/worked-examples`, z.array(workedExampleSchema)),
  sessions: () => request("/sessions", z.array(sessionSummarySchema)),
  session: (id: string) => request(`/sessions/${id}`, sessionSchema),
  startSession: (taskCodes?: string[]) => request("/sessions", sessionSchema, { method: "POST", body: taskCodes ? { task_codes: taskCodes } : {} }),
  endSession: (id: string, status: "COMPLETED" | "ABANDONED" = "COMPLETED") =>
    request(`/sessions/${id}/end`, sessionSchema, { method: "PATCH", body: { status } }),
  event: (sessionId: string, event: { event_type: ClientEventType; task_id: string; representation?: Representation; payload?: Record<string, unknown>; client_meta?: ClientMeta }) =>
    request(`/sessions/${sessionId}/events`, interactionSchema, { method: "POST", body: event }),
  submit: (sessionId: string, payload: ResponsePayload) => request(`/sessions/${sessionId}/responses`, submitResultSchema, { method: "POST", body: payload }),
  requestHelp: (sessionId: string, taskId: string, questionId?: string, clientMeta?: ClientMeta) =>
    request(`/sessions/${sessionId}/help`, helpOfferSchema, {
      method: "POST",
      body: { task_id: taskId, ...(questionId ? { question_id: questionId } : {}), ...(clientMeta ? { client_meta: clientMeta } : {}) },
    }),
  feedback: (sessionId: string, eventId: string, action: "ACCEPTED" | "REJECTED" | "REFORMULATE") =>
    request(`/sessions/${sessionId}/scaffold-events/${eventId}/feedback`, z.union([helpOfferSchema, scaffoldEventSchema]), { method: "POST", body: { action } }),
  responses: (sessionId: string, taskId?: string) => request(`/sessions/${sessionId}/responses${taskId ? `?task_id=${taskId}` : ""}`, z.array(responseOutSchema)),
  interactions: (sessionId: string, taskId?: string) => request(`/sessions/${sessionId}/interactions${taskId ? `?task_id=${taskId}` : ""}`, z.array(interactionSchema)),
  scaffoldEvents: (sessionId: string) => request(`/sessions/${sessionId}/scaffold-events`, z.array(scaffoldEventSchema)),
};

export const studentQueryKeys = {
  tasks: ["tasks"] as const,
  sessions: ["sessions"] as const,
  session: (id: string) => ["sessions", id] as const,
  examples: (taskId: string) => ["tasks", taskId, "examples"] as const,
  responses: (sessionId: string, taskId: string) => ["sessions", sessionId, "responses", taskId] as const,
};

export const TASK_TYPE_LABEL: Record<TaskType, string> = {
  NUMERIC_PATTERN: "Patrón numérico",
  FIGURAL_PATTERN: "Patrón figural",
  TABLE: "Tabla",
  GRAPH: "Gráfico",
  SYMBOLIC: "Expresión",
  JUSTIFICATION: "Justificación",
  TRANSFER: "Transferencia",
};

export const REPRESENTATION_LABEL: Record<Representation, string> = {
  VERBAL: "Palabras",
  NUMERIC: "Número",
  TABULAR: "Tabla",
  GRAPHIC: "Gráfico",
  SYMBOLIC: "Expresión",
};

import { z } from "zod";

import { request } from "@/lib/api";
import { config } from "@/lib/config";

export const participantSchema = z.object({
  student_id: z.string(),
  participant_code: z.string(),
  grade: z.string(),
  group_code: z.string().nullable(),
  institution_code: z.string(),
  research_status: z.string(),
  sessions: z.number(),
  tasks_worked: z.number(),
  interactions: z.number(),
  episodes: z.number(),
});
export type Participant = z.infer<typeof participantSchema>;

export const episodeSchema = z.object({
  id: z.string(),
  student_id: z.string(),
  participant_code: z.string().nullable(),
  session_id: z.string(),
  task_id: z.string(),
  task_code: z.string().nullable(),
  task_title: z.string().nullable(),
  trigger: z.string(),
  status: z.string(),
  close_reason: z.string().nullable(),
  summary: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  closed_at: z.string().nullable(),
  interaction_count: z.number(),
});
export type Episode = z.infer<typeof episodeSchema>;

export const timelineStepSchema = z.object({
  sequence: z.number(),
  timestamp: z.string(),
  phase: z.string(),
  event_type: z.string(),
  actor: z.enum(["STUDENT", "SYSTEM", "TEACHER"]),
  representation: z.string().nullable(),
  content: z.record(z.string(), z.unknown()).nullable(),
  help_level: z.number().nullable(),
  help_type: z.string().nullable(),
  help_text: z.string().nullable(),
  evaluation: z.record(z.string(), z.unknown()).nullable(),
  teacher_intervention: z.record(z.string(), z.unknown()).nullable(),
  system_interpretation: z.record(z.string(), z.unknown()).nullable().optional(),
  scaffold_decision: z.record(z.string(), z.unknown()).nullable().optional(),
  ai_interpretation: z.record(z.string(), z.unknown()).nullable().optional(),
  client_meta: z.record(z.string(), z.unknown()),
});
export type TimelineStep = z.infer<typeof timelineStepSchema>;

export const memoSchema = z.object({
  id: z.string(),
  researcher_code: z.string().nullable(),
  title: z.string(),
  episode_id: z.string().nullable(),
  participant_code: z.string().nullable(),
  session_id: z.string().nullable(),
  task_id: z.string().nullable(),
  observation: z.string().nullable(),
  interpretation: z.string().nullable(),
  emerging_question: z.string().nullable(),
  contradiction: z.string().nullable(),
  negative_case: z.string().nullable(),
  possible_category: z.string().nullable(),
  theoretical_sampling_need: z.string().nullable(),
  tags: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
  source: z.literal("RESEARCHER"),
});
export type Memo = z.infer<typeof memoSchema>;

export const episodeDetailSchema = episodeSchema.extend({
  context: z.record(z.string(), z.unknown()),
  timeline: z.array(timelineStepSchema),
  memos: z.array(memoSchema),
});
export type EpisodeDetail = z.infer<typeof episodeDetailSchema>;

export const comparisonSchema = z.object({
  a: episodeSchema,
  b: episodeSchema,
  dimensions: z.record(z.string(), z.object({ a: z.unknown(), b: z.unknown() })),
  note: z.string(),
});
export type Comparison = z.infer<typeof comparisonSchema>;

export const interviewSchema = z.object({
  id: z.string(),
  researcher_code: z.string().nullable(),
  title: z.string(),
  interviewee_kind: z.string(),
  participant_code: z.string().nullable(),
  teacher_code: z.string().nullable(),
  session_id: z.string().nullable(),
  task_id: z.string().nullable(),
  episode_id: z.string().nullable(),
  conducted_at: z.string(),
  notes: z.string().nullable(),
  responses: z.array(
    z.object({
      id: z.string(),
      order_index: z.number(),
      question: z.string(),
      answer: z.string().nullable(),
      related_episode_id: z.string().nullable(),
      observations: z.string().nullable(),
      memo_id: z.string().nullable(),
    }),
  ),
  created_at: z.string(),
});
export type Interview = z.infer<typeof interviewSchema>;

export interface MemoIn {
  title: string;
  episode_id?: string | null;
  participant_code?: string | null;
  observation?: string;
  interpretation?: string;
  emerging_question?: string;
  contradiction?: string;
  negative_case?: string;
  possible_category?: string;
  theoretical_sampling_need?: string;
  tags: string[];
}

export interface InterviewIn {
  title: string;
  interviewee_kind: "STUDENT" | "TEACHER";
  participant_code?: string;
  teacher_code?: string;
  episode_id?: string;
  conducted_at: string;
  notes?: string;
  responses: { question: string; answer?: string; observations?: string }[];
}

export type ExportDataset = "participants" | "sessions" | "interactions" | "episodes" | "scaffold_events" | "state_history" | "memos" | "interviews";
export type ExportFormat = "csv" | "json" | "jsonl" | "xlsx" | "pdf";

function qs(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter((e): e is [string, string] => Boolean(e[1]));
  return entries.length ? `?${new URLSearchParams(entries).toString()}` : "";
}

export const aiInteractionSchema = z.object({
  id: z.string(),
  session_id: z.string().nullable(),
  interaction_id: z.string().nullable(),
  scaffold_event_id: z.string().nullable(),
  provider: z.string(),
  model: z.string().nullable(),
  purpose: z.string(),
  prompt: z.record(z.string(), z.unknown()),
  raw_output: z.string().nullable(),
  validation: z.record(z.string(), z.unknown()),
  approved: z.boolean(),
  latency_ms: z.number().nullable(),
  created_at: z.string(),
});
export type AIInteraction = z.infer<typeof aiInteractionSchema>;

export const aiConfigSchema = z.object({
  enabled: z.boolean(),
  provider: z.string(),
  model: z.string().nullable(),
  timeout_ms: z.number(),
  max_calls_per_session: z.number(),
  key_configured: z.boolean(),
  purposes: z.array(z.string()),
  guarantees: z.array(z.string()),
});
export type AIConfig = z.infer<typeof aiConfigSchema>;

export const researchApi = {
  aiInteractions: () => request("/ai/interactions", z.array(aiInteractionSchema)),
  aiConfig: () => request("/ai/config", aiConfigSchema),
  participants: () => request("/research/participants", z.array(participantSchema)),
  episodes: (params: { student_id?: string; session_id?: string; trigger?: string } = {}) => request(`/research/episodes${qs(params)}`, z.array(episodeSchema)),
  episode: (id: string) => request(`/research/episodes/${id}`, episodeDetailSchema),
  sessionTimeline: (sessionId: string) => request(`/research/sessions/${sessionId}/timeline`, z.array(timelineStepSchema)),
  compare: (a: string, b: string) => request(`/research/episodes/compare${qs({ a, b })}`, comparisonSchema),
  createManualEpisode: (payload: { session_id: string; task_id: string; from_sequence: number; to_sequence: number }) =>
    request("/research/episodes", episodeSchema, { method: "POST", body: payload }),
  memos: (params: { episode_id?: string; tag?: string } = {}) => request(`/research/memos${qs(params)}`, z.array(memoSchema)),
  createMemo: (payload: MemoIn) => request("/research/memos", memoSchema, { method: "POST", body: payload }),
  updateMemo: (id: string, payload: MemoIn) => request(`/research/memos/${id}`, memoSchema, { method: "PUT", body: payload }),
  deleteMemo: (id: string) => request(`/research/memos/${id}`, z.unknown(), { method: "DELETE" }),
  interviews: () => request("/research/interviews", z.array(interviewSchema)),
  createInterview: (payload: InterviewIn) => request("/research/interviews", interviewSchema, { method: "POST", body: payload }),
  exportUrl: (dataset: ExportDataset, format: ExportFormat, sessionId?: string) =>
    `${config.apiBaseUrl}/research/export${qs({ dataset, format, session_id: sessionId })}`,
};

export const researchQueryKeys = {
  participants: ["research", "participants"] as const,
  episodes: (params: object) => ["research", "episodes", params] as const,
  episode: (id: string) => ["research", "episode", id] as const,
  sessionTimeline: (id: string) => ["research", "timeline", id] as const,
  compare: (a: string, b: string) => ["research", "compare", a, b] as const,
  memos: (params: object) => ["research", "memos", params] as const,
  interviews: ["research", "interviews"] as const,
};

export const TRIGGER_LABEL: Record<string, string> = {
  DIFFICULTY: "Dificultad (sistema)",
  HELP_REQUEST: "Solicitud de ayuda",
  STAGNATION: "Estancamiento (sistema)",
  UNCERTAINTY: "Incertidumbre (sistema)",
  IMPULSIVITY: "Impulsividad (sistema)",
  TEACHER: "Intervención docente",
  MANUAL: "Manual (investigador/a)",
};

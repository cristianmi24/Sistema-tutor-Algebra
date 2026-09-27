import { z } from "zod";

import { request } from "@/lib/api";

export const tutorRuleSchema = z.object({
  id: z.string(),
  code: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  priority: z.number(),
  min_consecutive: z.number(),
  conditions: z.record(z.string(), z.unknown()),
  actions: z.record(z.string(), z.unknown()),
  version: z.number(),
  is_active: z.boolean(),
});
export type TutorRule = z.infer<typeof tutorRuleSchema>;

export const bayesConfigSchema = z.object({
  id: z.string(),
  name: z.string(),
  version: z.number(),
  priors: z.record(z.string(), z.number()),
  likelihoods: z.record(z.string(), z.record(z.string(), z.record(z.string(), z.number()))),
  thresholds: z.record(z.string(), z.unknown()),
  is_active: z.boolean(),
});
export type BayesConfig = z.infer<typeof bayesConfigSchema>;

export const taskAdminSchema = z.object({
  id: z.string(),
  code: z.string(),
  task_type: z.string(),
  title: z.string(),
  skill: z.string(),
  difficulty: z.number(),
  grade_min: z.string(),
  grade_max: z.string(),
  statement: z.record(z.string(), z.unknown()),
  solution: z.record(z.string(), z.unknown()),
  related_task_id: z.string().nullable(),
  order_index: z.number(),
  version: z.number(),
  is_active: z.boolean(),
});
export type TaskAdmin = z.infer<typeof taskAdminSchema>;

export const scaffoldSchema = z.object({
  id: z.string(),
  code: z.string(),
  scaffold_type: z.string(),
  level: z.number(),
  applicable_task_types: z.array(z.string()),
  applicable_skills: z.array(z.string()),
  content: z.record(z.string(), z.unknown()),
  version: z.number(),
  is_active: z.boolean(),
});
export type Scaffold = z.infer<typeof scaffoldSchema>;

export interface TutorRuleIn {
  code: string;
  name: string;
  description?: string | null;
  priority: number;
  min_consecutive: number;
  conditions: Record<string, unknown>;
  actions: Record<string, unknown>;
  is_active: boolean;
}

export interface SimulationRequest {
  evidence: Record<string, unknown>;
  previous_state?: string;
  task_type?: string;
  skill?: string;
}

export const simulationSchema = z.object({
  evidence: z.record(z.string(), z.unknown()),
  posterior: z.object({ probabilities: z.record(z.string(), z.number()), need_support: z.number(), most_likely: z.string(), evidence_used: z.array(z.string()) }),
  rule_result: z.object({
    state: z.string(),
    level: z.number(),
    intervention: z.string().nullable(),
    fading: z.string(),
    rule_code: z.string().nullable(),
    matched: z.array(z.string()),
    confirmed: z.boolean(),
    explanation: z.string(),
  }),
  decision: z.record(z.string(), z.unknown()),
});
export type Simulation = z.infer<typeof simulationSchema>;

export const tutorApi = {
  rules: () => request("/tutor-rules", z.array(tutorRuleSchema)),
  updateRule: (id: string, payload: TutorRuleIn) => request(`/tutor-rules/${id}`, tutorRuleSchema, { method: "PUT", body: payload }),
  bayes: () => request("/bayesian-config", z.array(bayesConfigSchema)),
  tasks: () => request("/catalog/tasks", z.array(taskAdminSchema)),
  scaffolds: () => request("/catalog/scaffolds", z.array(scaffoldSchema)),
  simulate: (payload: SimulationRequest) => request("/scaffolding/decision", simulationSchema, { method: "POST", body: payload }),
};

export const tutorQueryKeys = {
  rules: ["tutor", "rules"] as const,
  bayes: ["tutor", "bayes"] as const,
  tasks: ["catalog", "tasks"] as const,
  scaffolds: ["catalog", "scaffolds"] as const,
};

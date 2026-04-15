/** API client for the incident-sim backend. */

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Checkpoint =
  | "detection"
  | "triage"
  | "escalation"
  | "communication"
  | "resolution"
  | "closure";

export type Priority = "P1" | "P2" | "P3" | "P4";
export type Impact = "high" | "medium" | "low";
export type Urgency = "high" | "medium" | "low";

export interface IncidentTicket {
  inc_number: string;
  title: string;
  description: string;
  category: string;
  affected_systems: string[];
  impact: Impact | null;
  urgency: Urgency | null;
  priority: Priority | null;
  affected_users: string;
  workaround: string;
  resolution: string;
  escalation_contacts: string[];
  communication_sent: string[];
  status: string;
  assigned_to: string;
  notes: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  checkpoint: Checkpoint | null;
}

export interface CheckpointScore {
  checkpoint: Checkpoint;
  score: number;
  max_score: number;
  feedback: string;
  missed_items: string[];
  good_decisions: string[];
}

export interface StartSessionResponse {
  session_id: string;
  scenario_title: string;
  scenario_summary: string;
  initial_message: string;
  ticket: IncidentTicket;
  current_checkpoint: Checkpoint;
}

export interface UserInputResponse {
  assistant_message: string;
  ticket: IncidentTicket;
  current_checkpoint: Checkpoint;
  checkpoint_complete: boolean;
  checkpoint_score: CheckpointScore | null;
  session_complete: boolean;
}

export interface SessionStateResponse {
  session_id: string;
  scenario_title: string;
  scenario_summary: string;
  current_checkpoint: Checkpoint;
  completed_checkpoints: Checkpoint[];
  ticket: IncidentTicket;
  conversation: ChatMessage[];
  is_complete: boolean;
}

export interface DebriefReport {
  session_id: string;
  scenario_title: string;
  scenario_type: string;
  scores: CheckpointScore[];
  overall_score: number;
  overall_feedback: string;
  total_possible: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  startSession(scenarioType?: string): Promise<StartSessionResponse> {
    return request("/session/start", {
      method: "POST",
      body: JSON.stringify({ scenario_type: scenarioType ?? null }),
    });
  },

  sendInput(sessionId: string, message: string): Promise<UserInputResponse> {
    return request(`/session/${sessionId}/input`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },

  getSession(sessionId: string): Promise<SessionStateResponse> {
    return request(`/session/${sessionId}`);
  },

  forceAdvance(sessionId: string): Promise<UserInputResponse> {
    return request(`/session/${sessionId}/advance`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },

  getDebrief(sessionId: string): Promise<DebriefReport> {
    return request(`/session/${sessionId}/debrief`);
  },

  listScenarios(): Promise<{ scenarios: { type: string; description: string }[] }> {
    return request("/scenarios");
  },
};

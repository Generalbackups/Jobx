// frontend/src/types/voice-assistant.ts
//
// Shared TypeScript types for the Voice AI Job Posting Assistant feature.
// These types are used across the context, components, and form integration.
// Field names MUST match agent/models.py JobPostingData exactly.

// ── Collected job posting data ────────────────────────────────────────────────
// Mirrors JobPostingData in agent/models.py.
// All fields are optional because they are filled incrementally during conversation.
export interface JobPostingFormData {
  // Core identification
  job_title?: string | null;
  company_name?: string | null;
  department?: string | null;

  // Location
  location?: string | null;
  work_type?: string | null;        // "remote" | "onsite" | "hybrid"

  // Employment
  employment_type?: string | null;  // "full-time" | "part-time" | "contract" | "internship"
  experience_level?: string | null; // "entry" | "mid" | "senior" | "lead" | "executive"
  experience_years_min?: number | null;
  experience_years_max?: number | null;

  // Compensation
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;    // "per year" | "per month"

  // Skills
  skills_required?: string[];
  skills_preferred?: string[];

  // Content
  job_description?: string | null;
  responsibilities?: string[];
  qualifications?: string[];
  benefits?: string[];

  // Logistics
  number_of_openings?: number | null;
  application_deadline?: string | null;  // ISO date "YYYY-MM-DD"

  // Session metadata — present in the payload but excluded from form fields
  session_id?: string | null;
  recruiter_user_id?: string | null;
}

// ── Voice session states ──────────────────────────────────────────────────────
export type VoiceSessionState =
  | "idle"        // Initial state. Session not started.
  | "connecting"  // Token fetch + LiveKit room connection in progress.
  | "active"      // Connected. Agent is in the room. Conversation is live.
  | "ending"      // End session initiated. Waiting for agent to finalize.
  | "ended"       // Session complete. All data collected. Room disconnected.
  | "error";      // Unrecoverable error. Show error message to user.

// ── Transcript entry ──────────────────────────────────────────────────────────
export interface TranscriptEntry {
  id: string;                         // unique key for React rendering
  role: "agent" | "user";
  content: string;
  timestamp: number;                  // Date.now() at time of receipt
  isFinal: boolean;                   // false = in-progress partial transcription
}

// ── DataChannel message types (agent → frontend) ─────────────────────────────
// These must match the JSON published by the Python agent's _publish_field_update
// and finalize_session methods.

export interface FieldUpdateMessage {
  type: "field_update";
  field: keyof JobPostingFormData;    // must be a valid JobPostingFormData key
  value: string | number | string[] | null;
}

export interface SessionCompleteMessage {
  type: "session_complete";
  job_data: JobPostingFormData;
}

export interface AgentStateMessage {
  type: "agent_state";
  state: "greeting" | "collecting" | "confirming" | "complete" | "error";
}

export interface SessionErrorMessage {
  type: "session_error";
  message: string;
}

// Union type for all inbound DataChannel messages
export type InboundDataMessage =
  | FieldUpdateMessage
  | SessionCompleteMessage
  | AgentStateMessage
  | SessionErrorMessage;

// ── DataChannel message types (frontend → agent) ──────────────────────────────
export interface EndSessionMessage {
  type: "end_session";
}

// ── API response types ────────────────────────────────────────────────────────
export interface VoiceSessionStartResponse {
  room_name: string;
  token: string;
  session_id: string;
}

// ── Context value type ────────────────────────────────────────────────────────
export interface VoiceAssistantContextValue {
  sessionState: VoiceSessionState;
  collectedFields: Partial<JobPostingFormData>;
  transcript: TranscriptEntry[];
  isAgentSpeaking: boolean;
  isMicMuted: boolean;
  errorMessage: string | null;
  startSession: () => Promise<void>;
  endSession: () => void;
  toggleMic: () => void;
}

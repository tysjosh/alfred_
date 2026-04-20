/**
 * TypeScript interfaces matching backend API types (backend/models.py).
 */

export type DecisionOutcome =
  | "EXECUTE_SILENTLY"
  | "EXECUTE_AND_NOTIFY"
  | "CONFIRM_BEFORE_EXECUTING"
  | "ASK_CLARIFYING_QUESTION"
  | "REFUSE";

export type RiskLevel = "low" | "medium" | "high";

export interface ConversationTurn {
  role: string;
  content: string;
  timestamp: string; // ISO 8601
}

export interface Action {
  type: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface DeterministicSignals {
  has_recent_conflict: boolean;
  has_pending_block: boolean;
  action_type: string;
  external_party: boolean;
  irreversible: boolean;
  missing_parameters: string[];
}

export interface LLMSignals {
  intent_clarity: number;
  risk_level: RiskLevel;
  consistency_with_history: boolean;
  ambiguity_detected: boolean;
  policy_violation: boolean;
}

export interface AllSignals {
  deterministic: DeterministicSignals;
  llm: LLMSignals;
}

export interface DecideRequest {
  action: Action;
  conversation_history: ConversationTurn[];
  user_profile?: Record<string, unknown> | null;
  openai_api_key?: string | null;
  openai_model?: string | null;
}

export interface DecideResponse {
  decision: DecisionOutcome;
  confidence_score: number;
  signals: AllSignals;
  explanation: string;
  why_not_others: string;
  fallback_reason: string | null;
  raw_llm_response: string | null;
  prompt_text: string | null;
}

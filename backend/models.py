"""Core Pydantic models for the Contextual Action Decision Engine."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DecisionOutcome(str, Enum):
    EXECUTE_SILENTLY = "EXECUTE_SILENTLY"
    EXECUTE_AND_NOTIFY = "EXECUTE_AND_NOTIFY"
    CONFIRM_BEFORE_EXECUTING = "CONFIRM_BEFORE_EXECUTING"
    ASK_CLARIFYING_QUESTION = "ASK_CLARIFYING_QUESTION"
    REFUSE = "REFUSE"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConversationTurn(BaseModel):
    role: str
    content: str
    timestamp: str  # ISO 8601


class Action(BaseModel):
    type: str
    description: str
    parameters: dict = Field(default_factory=dict)


class Context(BaseModel):
    action: Action
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    prior_decisions: list[DecisionOutcome] = Field(default_factory=list)
    user_profile: Optional[dict] = None


class DeterministicSignals(BaseModel):
    has_recent_conflict: bool = False
    has_pending_block: bool = False
    action_type: str = ""
    external_party: bool = False
    irreversible: bool = False
    missing_parameters: list[str] = Field(default_factory=list)


class LLMSignals(BaseModel):
    intent_clarity: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    consistency_with_history: bool
    ambiguity_detected: bool
    policy_violation: bool


class AllSignals(BaseModel):
    deterministic: DeterministicSignals
    llm: LLMSignals


class DecideRequest(BaseModel):
    action: Action
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    user_profile: Optional[dict] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None


class DecideResponse(BaseModel):
    decision: DecisionOutcome
    confidence_score: float = Field(ge=0.0, le=1.0)
    signals: AllSignals
    explanation: str
    why_not_others: str
    fallback_reason: Optional[str] = None
    raw_llm_response: Optional[str] = None
    prompt_text: Optional[str] = None

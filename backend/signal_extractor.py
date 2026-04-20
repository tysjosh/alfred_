"""Signal Extractor: computes deterministic and LLM-derived signals."""

import json
import os

import openai

from models import AllSignals, Context, DeterministicSignals, LLMSignals
from prompt_builder import PromptBuilder
from schemas import ACTION_SCHEMAS, IRREVERSIBLE_ACTIONS


class LLMExtractionError(Exception):
    """Raised when LLM signal extraction fails after retry."""
    pass

# Phrases that indicate a conflict or delay request
CONFLICT_PHRASES = ["hold off", "wait", "don't send yet", "cancel", "stop", "not yet", "delay"]

# Phrases that indicate a blocking instruction
BLOCKING_PHRASES = ["hold off", "wait for legal", "don't send yet", "wait", "stop"]

# Phrases that lift a prior block
LIFTING_PHRASES = ["ok go ahead", "send it now", "proceed", "go ahead", "approved"]

# Action types that target external parties
EXTERNAL_PARTY_ACTIONS = {"email_external", "financial_transfer"}


class SignalExtractor:
    def extract_deterministic(self, context: Context) -> DeterministicSignals:
        """Compute deterministic signals from the context.

        - has_recent_conflict: true if conflict phrase found in last 10 turns
        - has_pending_block: true if blocking phrase exists without subsequent lifting phrase
        - action_type: from action payload's type field
        - external_party: true for email_external, financial_transfer
        - irreversible: true if action type in IRREVERSIBLE_ACTIONS
        - missing_parameters: set difference of required schema fields minus provided params
        """
        action_type = context.action.type
        history = context.conversation_history

        has_recent_conflict = self._check_recent_conflict(history)
        has_pending_block = self._check_pending_block(history)
        external_party = action_type in EXTERNAL_PARTY_ACTIONS
        irreversible = action_type in IRREVERSIBLE_ACTIONS
        missing_parameters = self._compute_missing_parameters(action_type, context.action.parameters)

        return DeterministicSignals(
            has_recent_conflict=has_recent_conflict,
            has_pending_block=has_pending_block,
            action_type=action_type,
            external_party=external_party,
            irreversible=irreversible,
            missing_parameters=missing_parameters,
        )

    @staticmethod
    def _check_recent_conflict(history: list) -> bool:
        """Scan last 10 conversation turns for conflict phrases."""
        recent_turns = history[-10:] if len(history) > 10 else history
        for turn in recent_turns:
            content_lower = turn.content.lower()
            for phrase in CONFLICT_PHRASES:
                if phrase in content_lower:
                    return True
        return False

    @staticmethod
    def _check_pending_block(history: list) -> bool:
        """Check if a blocking phrase exists without a subsequent lifting phrase.

        Scans the full history. If a blocking phrase is found, it's considered
        pending unless a lifting phrase appears after it.
        """
        last_block_index = -1
        last_lift_index = -1

        for i, turn in enumerate(history):
            content_lower = turn.content.lower()
            for phrase in BLOCKING_PHRASES:
                if phrase in content_lower:
                    last_block_index = i
                    break
            for phrase in LIFTING_PHRASES:
                if phrase in content_lower:
                    last_lift_index = i
                    break

        if last_block_index == -1:
            return False
        return last_lift_index <= last_block_index

    @staticmethod
    def _compute_missing_parameters(action_type: str, provided_params: dict) -> list[str]:
        """Compute missing parameters as set difference of required minus provided."""
        if action_type not in ACTION_SCHEMAS:
            return []
        required = set(ACTION_SCHEMAS[action_type])
        provided = set(provided_params.keys())
        return sorted(required - provided)

    def extract_llm(self, context: Context, deterministic: DeterministicSignals, api_key: str | None = None, model: str | None = None) -> LLMSignals:
        """Invoke LLM to compute intent and risk signals.

        Builds a prompt via PromptBuilder, calls OpenAI, parses the response
        into LLMSignals. Retries once on malformed response. Raises
        LLMExtractionError on second failure so the caller can delegate to
        FailureHandler.
        """
        signals, _ = self.extract_llm_with_raw(context, deterministic, api_key=api_key, model=model)
        return signals

    def extract_llm_with_raw(self, context: Context, deterministic: DeterministicSignals, api_key: str | None = None, model: str | None = None) -> tuple[LLMSignals, str]:
        """Invoke LLM and return both parsed signals and raw response text.

        Returns:
            Tuple of (LLMSignals, raw_response_text).
        """
        prompt_builder = PromptBuilder()
        prompt = prompt_builder.build(context, deterministic)

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        resolved_model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        client = openai.OpenAI(api_key=resolved_key)

        last_error: Exception | None = None
        last_raw: str = ""
        for attempt in range(2):
            raw_text = self._call_openai(client, prompt, resolved_model)
            last_raw = raw_text
            try:
                return self._parse_llm_response(raw_text), raw_text
            except (json.JSONDecodeError, ValueError, KeyError, Exception) as exc:
                last_error = exc
                # First attempt failed — retry once
                continue

        raise LLMExtractionError(
            f"LLM returned malformed response after retry: {last_error}"
        )

    @staticmethod
    def _call_openai(client: openai.OpenAI, prompt: str, model: str = "gpt-4o-mini") -> str:
        """Call OpenAI chat completions and return the raw text response."""
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _parse_llm_response(raw_text: str) -> LLMSignals:
        """Parse raw LLM text into a validated LLMSignals model.

        Extracts JSON from the response (handles markdown code fences),
        then validates via Pydantic.
        """
        text = raw_text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        data = json.loads(text)
        # Pydantic validation handles range checks on intent_clarity
        # and enum validation on risk_level
        return LLMSignals(**data)

    def serialize(self, signals: AllSignals) -> str:
        """Serialize AllSignals to JSON string with validation."""
        return signals.model_dump_json()

    def deserialize(self, json_str: str) -> AllSignals:
        """Deserialize JSON string to AllSignals with validation.

        Raises pydantic.ValidationError for out-of-range field values
        (e.g., intent_clarity outside [0.0, 1.0], invalid risk_level).
        """
        return AllSignals.model_validate_json(json_str)

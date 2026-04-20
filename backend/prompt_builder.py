"""Prompt Builder: constructs LLM prompts from context and signals."""

import json

from models import Context, DeterministicSignals


class PromptBuilder:
    def build(self, context: Context, deterministic_signals: DeterministicSignals) -> str:
        """Construct a structured prompt for LLM signal extraction.

        The prompt includes:
        - System instructions for signal extraction
        - Full conversation history (each turn with role, content, timestamp)
        - Current action details (type, description, parameters)
        - All deterministic signals as structured input
        - Expected JSON output schema for LLM signals
        """
        sections: list[str] = []

        # --- System instructions ---
        sections.append(
            "You are a signal extraction engine for a contextual action decision system. "
            "Analyze the provided conversation history, current action, and deterministic signals, "
            "then return a JSON object with the following fields:\n"
            "- intent_clarity (float 0.0-1.0): how clear the user's intent is\n"
            "- risk_level (string: low, medium, or high): potential impact of executing the action\n"
            "- consistency_with_history (boolean): whether the action is consistent with conversation history\n"
            "- ambiguity_detected (boolean): whether the request is ambiguous\n"
            "- policy_violation (boolean): whether the action violates any policy"
        )

        # --- Conversation history ---
        sections.append("=== CONVERSATION HISTORY ===")
        if context.conversation_history:
            for turn in context.conversation_history:
                sections.append(
                    f"[{turn.role}] ({turn.timestamp}): {turn.content}"
                )
        else:
            sections.append("No conversation history provided.")

        # --- Current action details ---
        sections.append("=== CURRENT ACTION ===")
        sections.append(f"Action Type: {context.action.type}")
        sections.append(f"Action Description: {context.action.description}")
        sections.append(f"Action Parameters: {json.dumps(context.action.parameters)}")

        # --- Deterministic signals ---
        sections.append("=== DETERMINISTIC SIGNALS ===")
        sections.append(f"has_recent_conflict: {deterministic_signals.has_recent_conflict}")
        sections.append(f"has_pending_block: {deterministic_signals.has_pending_block}")
        sections.append(f"action_type: {deterministic_signals.action_type}")
        sections.append(f"external_party: {deterministic_signals.external_party}")
        sections.append(f"irreversible: {deterministic_signals.irreversible}")
        sections.append(f"missing_parameters: {json.dumps(deterministic_signals.missing_parameters)}")

        # --- Expected output schema ---
        sections.append("=== EXPECTED OUTPUT ===")
        sections.append(
            "Return ONLY a JSON object with exactly these fields:\n"
            "{\n"
            '  "intent_clarity": <float between 0.0 and 1.0>,\n'
            '  "risk_level": "<low|medium|high>",\n'
            '  "consistency_with_history": <true|false>,\n'
            '  "ambiguity_detected": <true|false>,\n'
            '  "policy_violation": <true|false>\n'
            "}"
        )

        return "\n".join(sections)

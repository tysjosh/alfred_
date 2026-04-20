"""Failure Handler: manages LLM failures and applies fallback logic."""

import json
import sys
from datetime import datetime, timezone

from decision_engine import DecisionResult
from models import Context, DecisionOutcome


class FailureHandler:
    def handle(self, failure_type: str, action_id: str, context: Context) -> DecisionResult:
        """Apply fallback logic for LLM failures.

        Args:
            failure_type: One of "llm_timeout", "malformed_response", "insufficient_context", "llm_error".
            action_id: Identifier for the action being evaluated.
            context: The Context object for the current request.

        Returns:
            DecisionResult with the appropriate fallback decision and reason.
        """
        if failure_type == "insufficient_context":
            decision = DecisionOutcome.ASK_CLARIFYING_QUESTION
            fallback_reason = "Insufficient context to evaluate intent; requesting clarification."
            explanation = (
                "The conversation history is insufficient to evaluate consistency signals. "
                "Asking a clarifying question to gather more context before proceeding."
            )
            why_not_others = (
                "EXECUTE_SILENTLY was ruled out because there is not enough context to confirm safety. "
                "EXECUTE_AND_NOTIFY was ruled out because risk cannot be assessed without sufficient history. "
                "CONFIRM_BEFORE_EXECUTING was ruled out because clarification is more appropriate than confirmation when context is missing. "
                "REFUSE was ruled out because there is no evidence of a policy violation."
            )
        elif failure_type == "llm_timeout":
            decision = DecisionOutcome.CONFIRM_BEFORE_EXECUTING
            fallback_reason = "LLM call timed out after 10 seconds; defaulting to confirmation."
            explanation = (
                "The LLM call timed out (>10s). Falling back to confirmation to ensure "
                "the action is not executed without review."
            )
            why_not_others = (
                "EXECUTE_SILENTLY was ruled out because LLM signals are unavailable due to timeout. "
                "EXECUTE_AND_NOTIFY was ruled out because risk level could not be assessed. "
                "ASK_CLARIFYING_QUESTION was ruled out because the issue is a system failure, not missing user input. "
                "REFUSE was ruled out because there is no evidence of a policy violation."
            )
        elif failure_type == "malformed_response":
            decision = DecisionOutcome.CONFIRM_BEFORE_EXECUTING
            fallback_reason = "LLM returned a malformed response after retry; defaulting to confirmation."
            explanation = (
                "The LLM returned a malformed response that could not be parsed after one retry. "
                "Falling back to confirmation to ensure the action is not executed without review."
            )
            why_not_others = (
                "EXECUTE_SILENTLY was ruled out because LLM signals are unavailable due to malformed response. "
                "EXECUTE_AND_NOTIFY was ruled out because risk level could not be assessed. "
                "ASK_CLARIFYING_QUESTION was ruled out because the issue is a system failure, not missing user input. "
                "REFUSE was ruled out because there is no evidence of a policy violation."
            )
        else:
            # llm_error (auth, network, rate limit, etc.)
            decision = DecisionOutcome.CONFIRM_BEFORE_EXECUTING
            fallback_reason = f"LLM service error ({failure_type}); defaulting to confirmation."
            explanation = (
                "The LLM service encountered an error (e.g., authentication failure, network issue, or rate limit). "
                "Falling back to confirmation to ensure the action is not executed without review."
            )
            why_not_others = (
                "EXECUTE_SILENTLY was ruled out because LLM signals are unavailable due to a service error. "
                "EXECUTE_AND_NOTIFY was ruled out because risk level could not be assessed. "
                "ASK_CLARIFYING_QUESTION was ruled out because the issue is a system failure, not missing user input. "
                "REFUSE was ruled out because there is no evidence of a policy violation."
            )

        # Log structured JSON to stdout
        log_entry = {
            "failure_type": failure_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_id": action_id,
            "fallback_decision": decision.value,
        }
        print(json.dumps(log_entry), file=sys.stdout, flush=True)

        return DecisionResult(
            decision=decision,
            explanation=explanation,
            why_not_others=why_not_others,
            confidence_score=0.0,
            fallback_reason=fallback_reason,
        )

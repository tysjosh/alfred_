"""Decision Engine: applies rule hierarchy and produces final decisions."""

from dataclasses import dataclass

from models import AllSignals, DecisionOutcome, RiskLevel


@dataclass
class DecisionResult:
    """Result of the decision engine evaluation."""
    decision: DecisionOutcome
    explanation: str
    why_not_others: str
    confidence_score: float = 0.0
    fallback_reason: str | None = None


class DecisionEngine:
    def decide(self, signals: AllSignals) -> DecisionResult:
        """Evaluate signals in strict priority order and return a decision."""
        det = signals.deterministic
        llm = signals.llm

        # Determine initial decision via strict priority order
        if llm.policy_violation:
            decision = DecisionOutcome.REFUSE
            reason = ""
        elif det.missing_parameters:
            decision = DecisionOutcome.ASK_CLARIFYING_QUESTION
            reason = "missing_parameters"
        elif llm.ambiguity_detected and llm.intent_clarity < 0.6:
            decision = DecisionOutcome.ASK_CLARIFYING_QUESTION
            reason = "ambiguous_intent"
        elif det.has_recent_conflict or det.has_pending_block:
            decision = DecisionOutcome.CONFIRM_BEFORE_EXECUTING
            reason = "conflict_or_block"
        elif llm.risk_level == RiskLevel.HIGH:
            decision = DecisionOutcome.CONFIRM_BEFORE_EXECUTING
            reason = "high_risk"
        elif llm.risk_level == RiskLevel.MEDIUM:
            decision = DecisionOutcome.EXECUTE_AND_NOTIFY
            reason = ""
        else:
            decision = DecisionOutcome.EXECUTE_SILENTLY
            reason = ""

        # Compute confidence and apply low-confidence gate
        confidence = self.compute_confidence(signals)
        if confidence < 0.5 and decision == DecisionOutcome.EXECUTE_SILENTLY:
            decision = DecisionOutcome.CONFIRM_BEFORE_EXECUTING
            reason = "low_confidence"

        return DecisionResult(
            decision=decision,
            confidence_score=confidence,
            explanation=self._build_explanation(decision, signals, reason=reason),
            why_not_others=self._build_why_not_others(decision, signals),
        )

    def _build_explanation(self, decision: DecisionOutcome, signals: AllSignals, reason: str = "") -> str:
        """Generate a human-readable explanation referencing specific signals."""
        det = signals.deterministic
        llm = signals.llm

        if decision == DecisionOutcome.REFUSE:
            return "Action refused because a policy violation was detected."

        if decision == DecisionOutcome.ASK_CLARIFYING_QUESTION:
            if reason == "ambiguous_intent":
                return (
                    f"Clarification needed: the LLM detected ambiguity in the user's intent "
                    f"(intent_clarity={llm.intent_clarity:.2f}, ambiguity_detected=true). "
                    f"The action's intent, target entity, or key parameters could not be confidently resolved from conversation history."
                )
            missing = ", ".join(det.missing_parameters)
            return f"Clarification needed: the following required parameters are missing: {missing}."

        if decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING:
            if reason == "conflict_or_block":
                parts = []
                if det.has_recent_conflict:
                    parts.append("a recent conflict was detected in conversation history")
                if det.has_pending_block:
                    parts.append("there is a pending block that has not been lifted")
                return f"Confirmation required because {' and '.join(parts)}."
            if reason == "high_risk":
                return "Confirmation required because the risk level is high."
            if reason == "low_confidence":
                return "Confirmation required because the confidence score is below the threshold (< 0.5), indicating uncertain intent."
            return "Confirmation required due to elevated risk signals."

        if decision == DecisionOutcome.EXECUTE_AND_NOTIFY:
            return f"Action will execute with notification because the risk level is medium (risk_level={llm.risk_level.value})."

        # EXECUTE_SILENTLY
        return f"Action will execute silently. Risk level is {llm.risk_level.value}, no policy violations, no missing parameters, and no conflicts detected."

    def _build_why_not_others(self, selected: DecisionOutcome, signals: AllSignals) -> str:
        """Describe why each non-selected outcome was ruled out."""
        det = signals.deterministic
        llm = signals.llm
        reasons = []

        all_outcomes = [
            DecisionOutcome.REFUSE,
            DecisionOutcome.ASK_CLARIFYING_QUESTION,
            DecisionOutcome.CONFIRM_BEFORE_EXECUTING,
            DecisionOutcome.EXECUTE_AND_NOTIFY,
            DecisionOutcome.EXECUTE_SILENTLY,
        ]

        for outcome in all_outcomes:
            if outcome == selected:
                continue

            if outcome == DecisionOutcome.REFUSE:
                reasons.append("REFUSE was ruled out because no policy violation was detected.")

            elif outcome == DecisionOutcome.ASK_CLARIFYING_QUESTION:
                if not det.missing_parameters and not (llm.ambiguity_detected and llm.intent_clarity < 0.6):
                    reasons.append("ASK_CLARIFYING_QUESTION was ruled out because all required parameters are present and intent is sufficiently clear.")
                elif not det.missing_parameters:
                    reasons.append("ASK_CLARIFYING_QUESTION was ruled out because all required parameters are present.")
                else:
                    reasons.append("ASK_CLARIFYING_QUESTION was ruled out because a higher-priority rule matched first.")

            elif outcome == DecisionOutcome.CONFIRM_BEFORE_EXECUTING:
                parts = []
                if not det.has_recent_conflict:
                    parts.append("no recent conflict")
                if not det.has_pending_block:
                    parts.append("no pending block")
                if llm.risk_level != RiskLevel.HIGH:
                    parts.append(f"risk level is {llm.risk_level.value} (not high)")
                reasons.append(f"CONFIRM_BEFORE_EXECUTING was ruled out because {', '.join(parts)}.")

            elif outcome == DecisionOutcome.EXECUTE_AND_NOTIFY:
                if llm.risk_level != RiskLevel.MEDIUM:
                    reasons.append(f"EXECUTE_AND_NOTIFY was ruled out because risk level is {llm.risk_level.value} (not medium).")
                else:
                    reasons.append("EXECUTE_AND_NOTIFY was ruled out because a higher-priority rule matched first.")

            elif outcome == DecisionOutcome.EXECUTE_SILENTLY:
                reasons.append("EXECUTE_SILENTLY was ruled out because a higher-priority rule matched first.")

        return " ".join(reasons)

    def compute_confidence(self, signals: AllSignals) -> float:
        """Derive confidence score from signals.

        Starts with intent_clarity, then applies strictly downward penalties
        for ambiguity_detected and has_recent_conflict. Result clamped to [0.0, 1.0].
        """
        confidence = signals.llm.intent_clarity

        if signals.llm.ambiguity_detected:
            confidence *= 0.7

        if signals.deterministic.has_recent_conflict:
            confidence *= 0.7

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

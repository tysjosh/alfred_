"""Unit tests for DecisionEngine.decide() — strict priority order, explanation, and why_not_others."""

import pytest
from models import (
    AllSignals,
    DecisionOutcome,
    DeterministicSignals,
    LLMSignals,
    RiskLevel,
)
from decision_engine import DecisionEngine, DecisionResult


@pytest.fixture
def engine():
    return DecisionEngine()


def _make_signals(
    policy_violation=False,
    missing_parameters=None,
    has_recent_conflict=False,
    has_pending_block=False,
    risk_level=RiskLevel.LOW,
    intent_clarity=0.9,
    consistency_with_history=True,
    ambiguity_detected=False,
) -> AllSignals:
    return AllSignals(
        deterministic=DeterministicSignals(
            has_recent_conflict=has_recent_conflict,
            has_pending_block=has_pending_block,
            action_type="test_action",
            external_party=False,
            irreversible=False,
            missing_parameters=missing_parameters or [],
        ),
        llm=LLMSignals(
            intent_clarity=intent_clarity,
            risk_level=risk_level,
            consistency_with_history=consistency_with_history,
            ambiguity_detected=ambiguity_detected,
            policy_violation=policy_violation,
        ),
    )


class TestDecisionPriorityOrder:
    """Test that the strict priority order is respected."""

    def test_policy_violation_returns_refuse(self, engine):
        signals = _make_signals(policy_violation=True)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.REFUSE

    def test_policy_violation_takes_priority_over_missing_params(self, engine):
        signals = _make_signals(policy_violation=True, missing_parameters=["recipient"])
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.REFUSE

    def test_missing_parameters_returns_ask(self, engine):
        signals = _make_signals(missing_parameters=["recipient", "subject"])
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.ASK_CLARIFYING_QUESTION

    def test_missing_params_takes_priority_over_conflict(self, engine):
        signals = _make_signals(missing_parameters=["amount"], has_recent_conflict=True)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.ASK_CLARIFYING_QUESTION

    def test_recent_conflict_returns_confirm(self, engine):
        signals = _make_signals(has_recent_conflict=True)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING

    def test_pending_block_returns_confirm(self, engine):
        signals = _make_signals(has_pending_block=True)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING

    def test_conflict_takes_priority_over_high_risk(self, engine):
        signals = _make_signals(has_recent_conflict=True, risk_level=RiskLevel.HIGH)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING

    def test_high_risk_returns_confirm(self, engine):
        signals = _make_signals(risk_level=RiskLevel.HIGH)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING

    def test_medium_risk_returns_execute_and_notify(self, engine):
        signals = _make_signals(risk_level=RiskLevel.MEDIUM)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.EXECUTE_AND_NOTIFY

    def test_low_risk_no_issues_returns_execute_silently(self, engine):
        signals = _make_signals(risk_level=RiskLevel.LOW)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.EXECUTE_SILENTLY


class TestExplanation:
    """Test that explanations are non-empty and reference relevant signals."""

    def test_refuse_explanation_mentions_policy(self, engine):
        result = engine.decide(_make_signals(policy_violation=True))
        assert result.explanation
        assert "policy violation" in result.explanation.lower()

    def test_ask_explanation_mentions_missing_params(self, engine):
        result = engine.decide(_make_signals(missing_parameters=["recipient", "subject"]))
        assert result.explanation
        assert "recipient" in result.explanation
        assert "subject" in result.explanation

    def test_confirm_conflict_explanation_mentions_conflict(self, engine):
        result = engine.decide(_make_signals(has_recent_conflict=True))
        assert result.explanation
        assert "conflict" in result.explanation.lower()

    def test_confirm_block_explanation_mentions_block(self, engine):
        result = engine.decide(_make_signals(has_pending_block=True))
        assert result.explanation
        assert "block" in result.explanation.lower()

    def test_confirm_high_risk_explanation_mentions_risk(self, engine):
        result = engine.decide(_make_signals(risk_level=RiskLevel.HIGH))
        assert result.explanation
        assert "risk" in result.explanation.lower()

    def test_notify_explanation_mentions_medium_risk(self, engine):
        result = engine.decide(_make_signals(risk_level=RiskLevel.MEDIUM))
        assert result.explanation
        assert "medium" in result.explanation.lower()

    def test_silent_explanation_is_nonempty(self, engine):
        result = engine.decide(_make_signals())
        assert result.explanation


class TestWhyNotOthers:
    """Test that why_not_others is non-empty and references non-selected outcomes."""

    def test_refuse_why_not_others_mentions_other_outcomes(self, engine):
        result = engine.decide(_make_signals(policy_violation=True))
        assert result.why_not_others
        assert "ASK_CLARIFYING_QUESTION" in result.why_not_others
        assert "CONFIRM_BEFORE_EXECUTING" in result.why_not_others
        assert "EXECUTE_AND_NOTIFY" in result.why_not_others
        assert "EXECUTE_SILENTLY" in result.why_not_others

    def test_silent_why_not_others_mentions_other_outcomes(self, engine):
        result = engine.decide(_make_signals())
        assert result.why_not_others
        assert "REFUSE" in result.why_not_others
        assert "ASK_CLARIFYING_QUESTION" in result.why_not_others
        assert "CONFIRM_BEFORE_EXECUTING" in result.why_not_others
        assert "EXECUTE_AND_NOTIFY" in result.why_not_others

    def test_why_not_others_does_not_mention_selected(self, engine):
        result = engine.decide(_make_signals(policy_violation=True))
        # REFUSE is selected, so it should not appear as "ruled out"
        assert "REFUSE was ruled out" not in result.why_not_others


class TestDecisionResultType:
    """Test that decide() returns a proper DecisionResult."""

    def test_returns_decision_result(self, engine):
        result = engine.decide(_make_signals())
        assert isinstance(result, DecisionResult)
        assert isinstance(result.decision, DecisionOutcome)
        assert isinstance(result.explanation, str)
        assert isinstance(result.why_not_others, str)


class TestComputeConfidence:
    """Test confidence derivation from intent_clarity with downward adjustments."""

    def test_confidence_equals_intent_clarity_when_no_penalties(self, engine):
        signals = _make_signals(intent_clarity=0.9, ambiguity_detected=False, has_recent_conflict=False)
        assert engine.compute_confidence(signals) == 0.9

    def test_confidence_reduced_by_ambiguity(self, engine):
        signals = _make_signals(intent_clarity=0.9, ambiguity_detected=True, has_recent_conflict=False)
        confidence = engine.compute_confidence(signals)
        assert confidence < 0.9
        assert confidence == pytest.approx(0.9 * 0.7)

    def test_confidence_reduced_by_conflict(self, engine):
        signals = _make_signals(intent_clarity=0.9, ambiguity_detected=False, has_recent_conflict=True)
        confidence = engine.compute_confidence(signals)
        assert confidence < 0.9
        assert confidence == pytest.approx(0.9 * 0.7)

    def test_confidence_reduced_by_both_ambiguity_and_conflict(self, engine):
        signals = _make_signals(intent_clarity=0.9, ambiguity_detected=True, has_recent_conflict=True)
        confidence = engine.compute_confidence(signals)
        assert confidence < 0.9 * 0.7  # double penalty
        assert confidence == pytest.approx(0.9 * 0.7 * 0.7)

    def test_confidence_clamped_to_zero(self, engine):
        signals = _make_signals(intent_clarity=0.0, ambiguity_detected=True, has_recent_conflict=True)
        assert engine.compute_confidence(signals) == 0.0

    def test_confidence_clamped_to_one(self, engine):
        signals = _make_signals(intent_clarity=1.0, ambiguity_detected=False, has_recent_conflict=False)
        assert engine.compute_confidence(signals) == 1.0

    def test_confidence_in_range(self, engine):
        signals = _make_signals(intent_clarity=0.5, ambiguity_detected=True)
        confidence = engine.compute_confidence(signals)
        assert 0.0 <= confidence <= 1.0


class TestLowConfidenceGate:
    """Test that low confidence overrides EXECUTE_SILENTLY to CONFIRM_BEFORE_EXECUTING."""

    def test_low_confidence_overrides_execute_silently(self, engine):
        # Low intent_clarity without ambiguity → confidence < 0.5 via conflict, overrides to CONFIRM
        signals = _make_signals(intent_clarity=0.3, ambiguity_detected=False, has_recent_conflict=True, risk_level=RiskLevel.LOW)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING

    def test_high_confidence_allows_execute_silently(self, engine):
        signals = _make_signals(intent_clarity=0.9, ambiguity_detected=False, risk_level=RiskLevel.LOW)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.EXECUTE_SILENTLY

    def test_low_confidence_does_not_override_other_decisions(self, engine):
        # Even with low confidence, REFUSE should stay REFUSE
        signals = _make_signals(intent_clarity=0.1, policy_violation=True)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.REFUSE

    def test_confidence_score_included_in_result(self, engine):
        signals = _make_signals(intent_clarity=0.8)
        result = engine.decide(signals)
        assert hasattr(result, 'confidence_score')
        assert 0.0 <= result.confidence_score <= 1.0

    def test_confidence_score_matches_compute_confidence(self, engine):
        signals = _make_signals(intent_clarity=0.7, ambiguity_detected=True)
        result = engine.decide(signals)
        expected = engine.compute_confidence(signals)
        assert result.confidence_score == expected

    def test_low_confidence_gate_explanation_mentions_confidence(self, engine):
        # Use low intent_clarity without ambiguity to hit the confidence gate (not the ambiguity→ASK path)
        signals = _make_signals(intent_clarity=0.4, ambiguity_detected=False, has_recent_conflict=False, risk_level=RiskLevel.LOW)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.CONFIRM_BEFORE_EXECUTING
        assert "confidence" in result.explanation.lower()

    def test_ambiguity_with_low_clarity_triggers_ask(self, engine):
        # ambiguity_detected + low intent_clarity → ASK_CLARIFYING_QUESTION
        signals = _make_signals(intent_clarity=0.3, ambiguity_detected=True, risk_level=RiskLevel.LOW)
        result = engine.decide(signals)
        assert result.decision == DecisionOutcome.ASK_CLARIFYING_QUESTION
        assert "ambiguity" in result.explanation.lower()

    def test_ambiguity_with_high_clarity_does_not_trigger_ask(self, engine):
        # ambiguity_detected but high intent_clarity → does NOT trigger ASK
        signals = _make_signals(intent_clarity=0.8, ambiguity_detected=True, risk_level=RiskLevel.LOW)
        result = engine.decide(signals)
        assert result.decision != DecisionOutcome.ASK_CLARIFYING_QUESTION

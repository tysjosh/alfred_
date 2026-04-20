"""Unit tests for SignalExtractor.extract_deterministic()."""

import pytest
from models import Action, Context, ConversationTurn, DeterministicSignals
from signal_extractor import SignalExtractor


@pytest.fixture
def extractor():
    return SignalExtractor()


def _make_turn(content: str, role: str = "user", timestamp: str = "2024-01-01T00:00:00Z") -> ConversationTurn:
    return ConversationTurn(role=role, content=content, timestamp=timestamp)


def _make_context(action_type: str = "reminder_self", params: dict | None = None, turns: list[ConversationTurn] | None = None) -> Context:
    return Context(
        action=Action(type=action_type, description="test", parameters=params or {}),
        conversation_history=turns or [],
    )


class TestHasRecentConflict:
    def test_no_history(self, extractor):
        ctx = _make_context()
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is False

    def test_conflict_in_recent_turns(self, extractor):
        turns = [_make_turn("please hold off on that")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is True

    def test_conflict_outside_last_10_turns(self, extractor):
        old_turn = _make_turn("hold off")
        filler = [_make_turn(f"normal message {i}") for i in range(10)]
        ctx = _make_context(turns=[old_turn] + filler)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is False

    def test_conflict_at_boundary_of_10(self, extractor):
        filler = [_make_turn(f"normal message {i}") for i in range(9)]
        conflict_turn = _make_turn("wait")
        ctx = _make_context(turns=[conflict_turn] + filler)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is True

    def test_multiple_conflict_phrases(self, extractor):
        turns = [_make_turn("don't send yet, cancel everything")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is True

    def test_case_insensitive(self, extractor):
        turns = [_make_turn("HOLD OFF please")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is True


class TestHasPendingBlock:
    def test_no_history(self, extractor):
        ctx = _make_context()
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is False

    def test_block_without_lift(self, extractor):
        turns = [_make_turn("hold off on that")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is True

    def test_block_followed_by_lift(self, extractor):
        turns = [_make_turn("hold off"), _make_turn("ok go ahead")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is False

    def test_lift_before_block(self, extractor):
        turns = [_make_turn("go ahead"), _make_turn("wait")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is True

    def test_block_lift_block(self, extractor):
        turns = [_make_turn("hold off"), _make_turn("go ahead"), _make_turn("stop")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is True

    def test_wait_for_legal(self, extractor):
        turns = [_make_turn("wait for legal review")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is True

    def test_approved_lifts_block(self, extractor):
        turns = [_make_turn("wait for legal"), _make_turn("approved")]
        ctx = _make_context(turns=turns)
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_pending_block is False


class TestActionType:
    def test_action_type_set(self, extractor):
        ctx = _make_context(action_type="email_external")
        signals = extractor.extract_deterministic(ctx)
        assert signals.action_type == "email_external"

    def test_unknown_action_type(self, extractor):
        ctx = _make_context(action_type="unknown_action")
        signals = extractor.extract_deterministic(ctx)
        assert signals.action_type == "unknown_action"


class TestExternalParty:
    def test_email_external(self, extractor):
        ctx = _make_context(action_type="email_external")
        signals = extractor.extract_deterministic(ctx)
        assert signals.external_party is True

    def test_financial_transfer(self, extractor):
        ctx = _make_context(action_type="financial_transfer")
        signals = extractor.extract_deterministic(ctx)
        assert signals.external_party is True

    def test_internal_action(self, extractor):
        ctx = _make_context(action_type="reminder_self")
        signals = extractor.extract_deterministic(ctx)
        assert signals.external_party is False


class TestIrreversible:
    def test_email_external_irreversible(self, extractor):
        ctx = _make_context(action_type="email_external")
        signals = extractor.extract_deterministic(ctx)
        assert signals.irreversible is True

    def test_financial_transfer_irreversible(self, extractor):
        ctx = _make_context(action_type="financial_transfer")
        signals = extractor.extract_deterministic(ctx)
        assert signals.irreversible is True

    def test_delete_permanent_irreversible(self, extractor):
        ctx = _make_context(action_type="delete_permanent")
        signals = extractor.extract_deterministic(ctx)
        assert signals.irreversible is True

    def test_reversible_action(self, extractor):
        ctx = _make_context(action_type="schedule_meeting")
        signals = extractor.extract_deterministic(ctx)
        assert signals.irreversible is False


class TestMissingParameters:
    def test_all_params_provided(self, extractor):
        ctx = _make_context(
            action_type="email_external",
            params={"recipient": "a", "subject": "b", "body": "c"},
        )
        signals = extractor.extract_deterministic(ctx)
        assert signals.missing_parameters == []

    def test_some_params_missing(self, extractor):
        ctx = _make_context(
            action_type="email_external",
            params={"recipient": "a"},
        )
        signals = extractor.extract_deterministic(ctx)
        assert set(signals.missing_parameters) == {"subject", "body"}

    def test_no_params_provided(self, extractor):
        ctx = _make_context(action_type="email_external", params={})
        signals = extractor.extract_deterministic(ctx)
        assert set(signals.missing_parameters) == {"recipient", "subject", "body"}

    def test_unknown_action_type_empty_missing(self, extractor):
        ctx = _make_context(action_type="unknown_action", params={})
        signals = extractor.extract_deterministic(ctx)
        assert signals.missing_parameters == []

    def test_extra_params_ignored(self, extractor):
        ctx = _make_context(
            action_type="reminder_self",
            params={"message": "hi", "time": "now", "extra": "ignored"},
        )
        signals = extractor.extract_deterministic(ctx)
        assert signals.missing_parameters == []


class TestUnknownActionDefaults:
    def test_unknown_action_returns_defaults(self, extractor):
        ctx = _make_context(action_type="totally_unknown")
        signals = extractor.extract_deterministic(ctx)
        assert signals.has_recent_conflict is False
        assert signals.has_pending_block is False
        assert signals.action_type == "totally_unknown"
        assert signals.external_party is False
        assert signals.irreversible is False
        assert signals.missing_parameters == []


"""Unit tests for SignalExtractor.extract_llm()."""

import json
from unittest.mock import MagicMock, patch

from models import LLMSignals, RiskLevel
from signal_extractor import LLMExtractionError


class TestParseLlmResponse:
    """Tests for _parse_llm_response static method."""

    def test_valid_json_response(self):
        raw = json.dumps({
            "intent_clarity": 0.85,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })
        result = SignalExtractor._parse_llm_response(raw)
        assert isinstance(result, LLMSignals)
        assert result.intent_clarity == 0.85
        assert result.risk_level == RiskLevel.LOW
        assert result.consistency_with_history is True
        assert result.ambiguity_detected is False
        assert result.policy_violation is False

    def test_json_with_markdown_code_fence(self):
        raw = '```json\n{"intent_clarity": 0.5, "risk_level": "medium", "consistency_with_history": true, "ambiguity_detected": true, "policy_violation": false}\n```'
        result = SignalExtractor._parse_llm_response(raw)
        assert result.intent_clarity == 0.5
        assert result.risk_level == RiskLevel.MEDIUM

    def test_invalid_intent_clarity_above_1(self):
        raw = json.dumps({
            "intent_clarity": 1.5,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })
        with pytest.raises(Exception):
            SignalExtractor._parse_llm_response(raw)

    def test_invalid_intent_clarity_below_0(self):
        raw = json.dumps({
            "intent_clarity": -0.1,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })
        with pytest.raises(Exception):
            SignalExtractor._parse_llm_response(raw)

    def test_invalid_risk_level(self):
        raw = json.dumps({
            "intent_clarity": 0.5,
            "risk_level": "extreme",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })
        with pytest.raises(Exception):
            SignalExtractor._parse_llm_response(raw)

    def test_malformed_json(self):
        with pytest.raises(json.JSONDecodeError):
            SignalExtractor._parse_llm_response("not json at all")

    def test_boundary_intent_clarity_0(self):
        raw = json.dumps({
            "intent_clarity": 0.0,
            "risk_level": "high",
            "consistency_with_history": False,
            "ambiguity_detected": True,
            "policy_violation": True,
        })
        result = SignalExtractor._parse_llm_response(raw)
        assert result.intent_clarity == 0.0

    def test_boundary_intent_clarity_1(self):
        raw = json.dumps({
            "intent_clarity": 1.0,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })
        result = SignalExtractor._parse_llm_response(raw)
        assert result.intent_clarity == 1.0


class TestExtractLlm:
    """Tests for extract_llm with mocked OpenAI calls."""

    def _valid_llm_json(self):
        return json.dumps({
            "intent_clarity": 0.9,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })

    def test_successful_extraction(self, extractor):
        ctx = _make_context()
        det = extractor.extract_deterministic(ctx)

        with patch.object(SignalExtractor, "_call_openai", return_value=self._valid_llm_json()):
            result = extractor.extract_llm(ctx, det)

        assert isinstance(result, LLMSignals)
        assert result.intent_clarity == 0.9
        assert result.risk_level == RiskLevel.LOW

    def test_retry_on_first_malformed_then_success(self, extractor):
        ctx = _make_context()
        det = extractor.extract_deterministic(ctx)

        with patch.object(
            SignalExtractor,
            "_call_openai",
            side_effect=["not valid json", self._valid_llm_json()],
        ):
            result = extractor.extract_llm(ctx, det)

        assert isinstance(result, LLMSignals)
        assert result.intent_clarity == 0.9

    def test_raises_after_two_malformed_responses(self, extractor):
        ctx = _make_context()
        det = extractor.extract_deterministic(ctx)

        with patch.object(
            SignalExtractor,
            "_call_openai",
            return_value="garbage",
        ):
            with pytest.raises(LLMExtractionError, match="malformed response after retry"):
                extractor.extract_llm(ctx, det)

    def test_raises_after_two_invalid_values(self, extractor):
        ctx = _make_context()
        det = extractor.extract_deterministic(ctx)

        bad_json = json.dumps({
            "intent_clarity": 2.0,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })

        with patch.object(
            SignalExtractor,
            "_call_openai",
            return_value=bad_json,
        ):
            with pytest.raises(LLMExtractionError):
                extractor.extract_llm(ctx, det)

    def test_retry_on_invalid_then_valid(self, extractor):
        ctx = _make_context()
        det = extractor.extract_deterministic(ctx)

        bad_json = json.dumps({
            "intent_clarity": -1.0,
            "risk_level": "low",
            "consistency_with_history": True,
            "ambiguity_detected": False,
            "policy_violation": False,
        })

        with patch.object(
            SignalExtractor,
            "_call_openai",
            side_effect=[bad_json, self._valid_llm_json()],
        ):
            result = extractor.extract_llm(ctx, det)

        assert result.intent_clarity == 0.9


from pydantic import ValidationError
from models import AllSignals


def _make_all_signals(**llm_overrides) -> AllSignals:
    """Helper to build a valid AllSignals with optional LLM signal overrides."""
    det = DeterministicSignals(
        has_recent_conflict=False,
        has_pending_block=False,
        action_type="reminder_self",
        external_party=False,
        irreversible=False,
        missing_parameters=[],
    )
    llm_defaults = {
        "intent_clarity": 0.8,
        "risk_level": "low",
        "consistency_with_history": True,
        "ambiguity_detected": False,
        "policy_violation": False,
    }
    llm_defaults.update(llm_overrides)
    llm = LLMSignals(**llm_defaults)
    return AllSignals(deterministic=det, llm=llm)


class TestSerialize:
    """Tests for SignalExtractor.serialize() — Requirement 11.1"""

    def test_serialize_returns_json_string(self, extractor):
        signals = _make_all_signals()
        result = extractor.serialize(signals)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "deterministic" in parsed
        assert "llm" in parsed

    def test_serialize_preserves_values(self, extractor):
        signals = _make_all_signals(intent_clarity=0.42, risk_level="high")
        result = extractor.serialize(signals)
        parsed = json.loads(result)
        assert parsed["llm"]["intent_clarity"] == 0.42
        assert parsed["llm"]["risk_level"] == "high"
        assert parsed["deterministic"]["action_type"] == "reminder_self"


class TestDeserialize:
    """Tests for SignalExtractor.deserialize() — Requirement 11.2"""

    def test_deserialize_valid_json(self, extractor):
        signals = _make_all_signals()
        json_str = extractor.serialize(signals)
        result = extractor.deserialize(json_str)
        assert isinstance(result, AllSignals)
        assert result == signals

    def test_deserialize_rejects_invalid_intent_clarity(self, extractor):
        bad_json = json.dumps({
            "deterministic": {
                "has_recent_conflict": False,
                "has_pending_block": False,
                "action_type": "reminder_self",
                "external_party": False,
                "irreversible": False,
                "missing_parameters": [],
            },
            "llm": {
                "intent_clarity": 1.5,
                "risk_level": "low",
                "consistency_with_history": True,
                "ambiguity_detected": False,
                "policy_violation": False,
            },
        })
        with pytest.raises(ValidationError):
            extractor.deserialize(bad_json)

    def test_deserialize_rejects_negative_intent_clarity(self, extractor):
        bad_json = json.dumps({
            "deterministic": {
                "has_recent_conflict": False,
                "has_pending_block": False,
                "action_type": "reminder_self",
                "external_party": False,
                "irreversible": False,
                "missing_parameters": [],
            },
            "llm": {
                "intent_clarity": -0.1,
                "risk_level": "low",
                "consistency_with_history": True,
                "ambiguity_detected": False,
                "policy_violation": False,
            },
        })
        with pytest.raises(ValidationError):
            extractor.deserialize(bad_json)

    def test_deserialize_rejects_invalid_risk_level(self, extractor):
        bad_json = json.dumps({
            "deterministic": {
                "has_recent_conflict": False,
                "has_pending_block": False,
                "action_type": "reminder_self",
                "external_party": False,
                "irreversible": False,
                "missing_parameters": [],
            },
            "llm": {
                "intent_clarity": 0.5,
                "risk_level": "extreme",
                "consistency_with_history": True,
                "ambiguity_detected": False,
                "policy_violation": False,
            },
        })
        with pytest.raises(ValidationError):
            extractor.deserialize(bad_json)

    def test_deserialize_rejects_malformed_json(self, extractor):
        with pytest.raises(ValidationError):
            extractor.deserialize("not valid json")


class TestSerializeRoundTrip:
    """Tests for round-trip serialization — Requirement 11.2"""

    def test_round_trip_preserves_equality(self, extractor):
        signals = _make_all_signals(
            intent_clarity=0.65,
            risk_level="medium",
            ambiguity_detected=True,
        )
        json_str = extractor.serialize(signals)
        restored = extractor.deserialize(json_str)
        assert restored == signals

    def test_round_trip_with_all_risk_levels(self, extractor):
        for level in ["low", "medium", "high"]:
            signals = _make_all_signals(risk_level=level)
            restored = extractor.deserialize(extractor.serialize(signals))
            assert restored == signals

    def test_round_trip_boundary_intent_clarity(self, extractor):
        for val in [0.0, 1.0]:
            signals = _make_all_signals(intent_clarity=val)
            restored = extractor.deserialize(extractor.serialize(signals))
            assert restored.llm.intent_clarity == val

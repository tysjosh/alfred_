"""Unit tests for ContextBuilder."""

import pytest
from context_builder import ContextBuilder
from models import Action, ConversationTurn, DecisionOutcome


@pytest.fixture
def builder():
    return ContextBuilder()


@pytest.fixture
def sample_action():
    return Action(type="email_external", description="Send email", parameters={"recipient": "alice@example.com"})


class TestContextBuilderBuild:
    def test_empty_history_returns_empty_list(self, builder, sample_action):
        ctx = builder.build(action=sample_action, conversation_history=None)
        assert ctx.conversation_history == []
        assert ctx.prior_decisions == []
        assert ctx.action == sample_action

    def test_empty_list_history(self, builder, sample_action):
        ctx = builder.build(action=sample_action, conversation_history=[])
        assert ctx.conversation_history == []

    def test_preserves_action(self, builder, sample_action):
        ctx = builder.build(action=sample_action)
        assert ctx.action.type == "email_external"
        assert ctx.action.description == "Send email"
        assert ctx.action.parameters == {"recipient": "alice@example.com"}

    def test_preserves_user_profile(self, builder, sample_action):
        profile = {"name": "Alice", "role": "admin"}
        ctx = builder.build(action=sample_action, user_profile=profile)
        assert ctx.user_profile == profile

    def test_none_user_profile(self, builder, sample_action):
        ctx = builder.build(action=sample_action, user_profile=None)
        assert ctx.user_profile is None

    def test_sorts_history_chronologically(self, builder, sample_action):
        turns = [
            ConversationTurn(role="user", content="second", timestamp="2024-01-01T00:02:00Z"),
            ConversationTurn(role="user", content="first", timestamp="2024-01-01T00:01:00Z"),
            ConversationTurn(role="user", content="third", timestamp="2024-01-01T00:03:00Z"),
        ]
        ctx = builder.build(action=sample_action, conversation_history=turns)
        assert [t.content for t in ctx.conversation_history] == ["first", "second", "third"]

    def test_preserves_all_turns(self, builder, sample_action):
        turns = [
            ConversationTurn(role="user", content="hello", timestamp="2024-01-01T00:01:00Z"),
            ConversationTurn(role="assistant", content="hi", timestamp="2024-01-01T00:02:00Z"),
        ]
        ctx = builder.build(action=sample_action, conversation_history=turns)
        assert len(ctx.conversation_history) == 2
        assert ctx.conversation_history[0].role == "user"
        assert ctx.conversation_history[1].role == "assistant"

    def test_preserves_timestamps(self, builder, sample_action):
        turns = [
            ConversationTurn(role="user", content="msg", timestamp="2024-06-15T10:30:00Z"),
        ]
        ctx = builder.build(action=sample_action, conversation_history=turns)
        assert ctx.conversation_history[0].timestamp == "2024-06-15T10:30:00Z"

    def test_extracts_prior_decisions_from_assistant_turns(self, builder, sample_action):
        turns = [
            ConversationTurn(role="user", content="do something", timestamp="2024-01-01T00:01:00Z"),
            ConversationTurn(role="assistant", content="Decision: REFUSE", timestamp="2024-01-01T00:02:00Z"),
            ConversationTurn(role="assistant", content="Outcome was EXECUTE_SILENTLY", timestamp="2024-01-01T00:03:00Z"),
        ]
        ctx = builder.build(action=sample_action, conversation_history=turns)
        assert DecisionOutcome.REFUSE in ctx.prior_decisions
        assert DecisionOutcome.EXECUTE_SILENTLY in ctx.prior_decisions

    def test_ignores_user_turns_for_decisions(self, builder, sample_action):
        turns = [
            ConversationTurn(role="user", content="REFUSE this", timestamp="2024-01-01T00:01:00Z"),
        ]
        ctx = builder.build(action=sample_action, conversation_history=turns)
        assert ctx.prior_decisions == []

    def test_no_decisions_when_none_present(self, builder, sample_action):
        turns = [
            ConversationTurn(role="assistant", content="Sure, I can help.", timestamp="2024-01-01T00:01:00Z"),
        ]
        ctx = builder.build(action=sample_action, conversation_history=turns)
        assert ctx.prior_decisions == []

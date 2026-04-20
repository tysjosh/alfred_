"""Context Builder: assembles structured context from incoming requests."""

from models import Action, Context, ConversationTurn, DecisionOutcome


class ContextBuilder:
    def build(
        self,
        action: Action,
        conversation_history: list[ConversationTurn] | None = None,
        user_profile: dict | None = None,
    ) -> Context:
        """Assemble a Context object from action, conversation history, and optional user profile.

        - Preserves chronological order of conversation turns (sorted by timestamp).
        - Returns Context with empty history array if conversation_history is absent/empty.
        - Extracts prior DecisionOutcome values from assistant turns in conversation history.
        """
        if not conversation_history:
            sorted_history: list[ConversationTurn] = []
        else:
            sorted_history = sorted(conversation_history, key=lambda turn: turn.timestamp)

        prior_decisions = self._extract_prior_decisions(sorted_history)

        return Context(
            action=action,
            conversation_history=sorted_history,
            prior_decisions=prior_decisions,
            user_profile=user_profile,
        )

    @staticmethod
    def _extract_prior_decisions(history: list[ConversationTurn]) -> list[DecisionOutcome]:
        """Scan assistant turns for DecisionOutcome strings and return them in order."""
        decisions: list[DecisionOutcome] = []
        for turn in history:
            if turn.role != "assistant":
                continue
            for outcome in DecisionOutcome:
                if outcome.value in turn.content:
                    decisions.append(outcome)
        return decisions

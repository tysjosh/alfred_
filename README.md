# Contextual Action Decision Engine

A hybrid decision system that evaluates user-initiated actions against conversation history, intent signals, and risk factors. It combines deterministic rule-based logic with LLM reasoning to produce one of five decision outcomes — each accompanied by a confidence score, a full reasoning chain, and a "why not others" explanation.

Built for the [Alfred Application Challenge](alfred_application_challenge.pdf).

---

## Live Demo

- **Live URL:** `https://your-deployment-url.example.com` *(placeholder — update after deployment)*
- **GitHub:** `https://github.com/your-username/contextual-action-decision-engine` *(placeholder — update after publishing)*

---

## Architecture

The system follows a strictly sequential pipeline:

```
User Action + Context
        │
        ▼
  ┌─────────────┐
  │Context Builder│  ← Assembles conversation history, action, user profile
  └──────┬──────┘
         ▼
  ┌──────────────┐
  │Signal Extractor│
  │  ├─ Deterministic signals (rule-based, instant)
  │  └─ LLM signals (OpenAI, single call)
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │Decision Engine│  ← Strict priority rules + confidence gate
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │   Response    │  ← Decision + explanation + debug data
  └──────────────┘
```

**Backend:** Python + FastAPI · **Frontend:** React + TypeScript (Vite) · **LLM:** OpenAI (gpt-4o-mini)

All failure paths default to safe outcomes (`CONFIRM_BEFORE_EXECUTING` or `ASK_CLARIFYING_QUESTION`) — the system never silently executes when uncertain.

---

## Signals Documentation

The engine extracts two categories of signals from every request.

### Deterministic Signals

These are computed instantly with pure logic — no LLM involved. They are fast, auditable, and fully reproducible.

| Signal | Type | Description |
|---|---|---|
| `has_recent_conflict` | `boolean` | `true` if the conversation history (last 10 turns) contains a phrase that contradicts or delays the current action (e.g., "hold off", "wait", "don't send yet"). |
| `has_pending_block` | `boolean` | `true` if a blocking instruction exists in history (e.g., "wait for legal") that has **not** been explicitly lifted by a subsequent phrase like "go ahead" or "approved". |
| `action_type` | `string` | The type of the submitted action (e.g., `email_external`, `financial_transfer`, `schedule_meeting`, `reminder_self`). Drives schema validation and irreversibility checks. |
| `external_party` | `boolean` | `true` when the action targets a recipient or system outside the user's organization. Applies to `email_external` and `financial_transfer`. |
| `irreversible` | `boolean` | `true` for action types that cannot be undone: `email_external`, `financial_transfer`, `delete_permanent`. |
| `missing_parameters` | `string[]` | The list of required parameters (per the action schema registry) that are absent from the action payload. Computed as the set difference of required fields minus provided fields. |

### LLM-Derived Signals

These are computed by a single OpenAI call that receives the full conversation history, current action, and all deterministic signals as structured input.

| Signal | Type | Description |
|---|---|---|
| `intent_clarity` | `float [0.0–1.0]` | How clearly the user's intent can be understood from the conversation context. Higher values mean the LLM is more confident about what the user wants. |
| `risk_level` | `low \| medium \| high` | The potential impact of executing the action, considering factors like financial exposure, external visibility, and irreversibility. |
| `consistency_with_history` | `boolean` | Whether the current action is consistent with the user's prior statements and behavior in the conversation. |
| `ambiguity_detected` | `boolean` | `true` if the LLM detects ambiguity in the user's request — vague references, incomplete instructions, or contradictory signals. |
| `policy_violation` | `boolean` | `true` if the action conflicts with a defined system or organizational rule (e.g., sending confidential data externally, exceeding spending limits). |

---

## Decision Logic

The Decision Engine applies a **strict priority order** — it evaluates rules top-to-bottom and returns the **first match**:

| Priority | Condition | Decision Outcome |
|---|---|---|
| 1 | `policy_violation` is `true` | **REFUSE** — Action is blocked entirely. |
| 2 | `missing_parameters` is non-empty | **ASK_CLARIFYING_QUESTION** — Request the missing information. |
| 3 | `has_recent_conflict` or `has_pending_block` is `true` | **CONFIRM_BEFORE_EXECUTING** — Ask user to confirm given the contradiction. |
| 4 | `risk_level` is `high` | **CONFIRM_BEFORE_EXECUTING** — High-risk actions require explicit confirmation. |
| 5 | `risk_level` is `medium` | **EXECUTE_AND_NOTIFY** — Proceed but inform the user. |
| 6 | None of the above | **EXECUTE_SILENTLY** — Safe to proceed without interruption. |

**Confidence gate:** If the computed `confidence_score` falls below **0.5**, the engine will never return `EXECUTE_SILENTLY` — it upgrades to `CONFIRM_BEFORE_EXECUTING` instead.

### The 5 Decision Outcomes

- **EXECUTE_SILENTLY** — Low risk, clear intent, no conflicts. Action proceeds without interruption.
- **EXECUTE_AND_NOTIFY** — Medium risk. Action proceeds, but the user is notified.
- **CONFIRM_BEFORE_EXECUTING** — Conflicts, high risk, or low confidence detected. User must explicitly confirm.
- **ASK_CLARIFYING_QUESTION** — Required parameters are missing or context is insufficient.
- **REFUSE** — A policy violation was detected. Action is blocked.

---

## LLM vs Deterministic Rationale

A core design decision is **which logic runs deterministically and which is delegated to the LLM**. The boundary is drawn based on whether the task requires structured pattern matching or nuanced language understanding.

### Why Deterministic

| Logic | Rationale |
|---|---|
| **Conflict detection** (`has_recent_conflict`) | Conflict phrases ("hold off", "wait", "don't send yet") are a finite, well-defined set. Pattern matching is faster, cheaper, and fully auditable — no LLM needed. |
| **Block detection** (`has_pending_block`) | Same as conflict detection: blocking and lifting phrases are enumerable. The logic is a simple scan for the most recent block/lift pair. |
| **Parameter validation** (`missing_parameters`) | Schema validation is a pure set operation (required fields minus provided fields). This is a solved problem that doesn't benefit from LLM reasoning. |
| **Irreversibility classification** (`irreversible`) | Whether an action type is irreversible is a static property defined at design time. It's a set membership check. |
| **External party detection** (`external_party`) | Determined by action type. No interpretation needed. |

### Why LLM

| Logic | Rationale |
|---|---|
| **Intent clarity** (`intent_clarity`) | Understanding *how clear* a user's intent is requires reading between the lines of conversation context. "Send it" after a vague draft is very different from "Send it" after a fully specified email. |
| **Risk assessment** (`risk_level`) | Risk depends on the combination of action type, parameters, conversation context, and real-world impact. A $50 transfer and a $50,000 transfer have different risk profiles that require contextual judgment. |
| **Consistency with history** (`consistency_with_history`) | Determining whether an action is consistent with prior conversation requires semantic understanding of what was discussed, not just keyword matching. |
| **Ambiguity detection** (`ambiguity_detected`) | Ambiguity is inherently a language understanding problem. Vague pronouns, incomplete references, and implicit assumptions require LLM-level comprehension. |
| **Policy violation detection** (`policy_violation`) | Policies can be complex and context-dependent. The LLM can reason about whether an action violates organizational rules that may not be reducible to simple pattern matching. |

**The guiding principle:** If the logic can be expressed as a lookup table, set operation, or pattern match — it's deterministic. If it requires reading comprehension or contextual judgment — it's LLM.

---

## Known Failure Modes

### 1. LLM Hallucination of Signal Values

The LLM may return signal values that don't reflect reality — for example, reporting `risk_level: low` for a high-value financial transfer, or `policy_violation: true` when no policy exists. The system mitigates this with Pydantic validation (rejecting out-of-range values) and a single retry on malformed responses, but **semantic** hallucination (valid format, wrong content) cannot be caught automatically.

### 2. Missing or Insufficient Context Leading to Incorrect Decisions

When conversation history is empty or minimal, the LLM has little to work with. It may default to overly conservative or overly permissive signal values. The Failure Handler catches the extreme case (empty history → `ASK_CLARIFYING_QUESTION`), but borderline cases with *some* history that is still insufficient may produce unreliable decisions.

### 3. Contradictory Instructions in Conversation History

If a user says "hold off" and then later says "go ahead" but then says "actually wait" — the system tracks the *most recent* block/lift pair. Complex multi-turn contradictions where intent shifts multiple times may not be resolved correctly, especially when the contradictions are implicit rather than using exact blocking/lifting phrases.

### 4. Conflict Phrase Sensitivity

The deterministic conflict detection relies on a fixed set of phrases ("hold off", "wait", "don't send yet", etc.). Paraphrased conflicts like "let's pump the brakes on that" or "I'm not ready for that to go out" will not be detected by the deterministic layer. The LLM's `consistency_with_history` signal may catch these, but it's not guaranteed.

---

## Evolving with Riskier Tools

As Alfred gains access to higher-stakes tools (e.g., production deployments, legal document signing, HR actions, multi-step financial workflows), the decision engine is designed to scale its safety guarantees without architectural rewrites.

**Tiered action classification.** The current `IRREVERSIBLE_ACTIONS` set is a flat list. This would evolve into a multi-tier risk taxonomy — low/medium/high/critical — where each tier has its own confirmation requirements. Critical-tier actions (e.g., deploying to production, signing contracts) could require multi-factor confirmation: both an explicit user confirm *and* a secondary approval from a designated reviewer.

**Dynamic schema registry.** Today `ACTION_SCHEMAS` is a static dictionary. As tools proliferate, this becomes a plugin-based registry where each new tool self-declares its required parameters, risk tier, reversibility, and any domain-specific policy constraints. New tools get safe defaults (high risk, confirmation required) until explicitly classified.

**Composite action graphs.** Single-action evaluation won't suffice when Alfred chains tools together (e.g., "draft the contract, get legal review, then send to client"). The engine would need to evaluate action *sequences* — checking that the aggregate risk of a chain doesn't exceed thresholds, and that intermediate steps don't create irreversible side effects before confirmation gates.

**Escalation policies.** For the riskiest tools, the decision engine would support escalation beyond the immediate user — routing confirmation requests to team leads, compliance officers, or automated approval workflows. The `CONFIRM_BEFORE_EXECUTING` outcome would branch into `CONFIRM_USER` vs `CONFIRM_ESCALATED` depending on the action's risk tier.

**Rate limiting and anomaly detection.** High-risk tools would have per-user and per-session rate limits (e.g., no more than 3 financial transfers per hour without escalation). The signal extractor would gain a `velocity_anomaly` signal that flags unusual patterns — a sudden burst of delete operations or transfers to new recipients.

**Audit trail with immutable logging.** Every decision for critical-tier actions would be written to an append-only audit log with cryptographic integrity, enabling post-hoc compliance review and forensic analysis if something goes wrong.


## Preloaded Scenarios

The UI includes 7 preloaded scenarios that can be loaded with a single click. They cover the full decision spectrum:

| # | Scenario | Expected Outcome | Category |
|---|---|---|---|
| 1 | **Self-reminder** — User sets a personal reminder ("Remind me to buy groceries at 5pm"). Low risk, no external party. | `EXECUTE_SILENTLY` | Easy |
| 2 | **Calendar event** — User adds a team standup with all required parameters (title, time, duration). | `EXECUTE_AND_NOTIFY` | Easy |
| 3 | **"Send it" after unclear draft** — User says "Send it" but recipient, subject, and body are all missing from the email action. | `ASK_CLARIFYING_QUESTION` | Ambiguous |
| 4 | **Meeting without time** — User wants to schedule a meeting but the required "time" parameter is missing. | `ASK_CLARIFYING_QUESTION` | Ambiguous |
| 5 | **Email after "hold off"** — User previously said "hold off on sending anything to the client" but now asks to send the proposal. Conflict detected. | `CONFIRM_BEFORE_EXECUTING` | Adversarial |
| 6 | **Financial transfer** — High-value $5,000 vendor payment. Irreversible action with high risk. | `CONFIRM_BEFORE_EXECUTING` | Adversarial |
| 7 | **⚠️ LLM Timeout Simulation** — Simulates an LLM failure to demonstrate the fallback path. Returns `fallback_reason` in the debug view. | `CONFIRM_BEFORE_EXECUTING` | Failure Demo |

---

## 6-Month Roadmap

### Month 1–2: Reliability & Observability
- **Multi-model fallback** — Add Claude as a fallback when OpenAI is unavailable or slow. Automatic failover with latency-based routing.
- **Audit dashboard** — Structured logging of every decision with searchable history. Track decision distribution, fallback rates, and confidence score trends.
- **Prompt versioning** — Version-control prompts so changes to LLM instructions can be tracked, compared, and rolled back.

### Month 3–4: Tuning & Feedback
- **User feedback loop** — Allow users to mark decisions as correct/incorrect. Use this data to identify systematic errors and tune thresholds.
- **Signal weighting tuning** — Make confidence adjustments (currently hardcoded 0.7 multipliers) configurable per deployment. A/B test different weighting schemes.
- **Expanded conflict detection** — Use the LLM to detect paraphrased conflicts beyond the fixed phrase list, with a deterministic fast-path for known phrases.

### Month 5–6: Scale & Capabilities
- **Multi-action batching** — Support evaluating multiple actions in a single request for workflow automation scenarios.
- **Custom policy rules** — Allow operators to define organization-specific policy rules that feed into the `policy_violation` signal without modifying code.
- **Streaming explanations** — Stream the decision explanation in real time as the LLM generates it, reducing perceived latency.
- **Historical context window** — Extend beyond single-session conversation history to include cross-session user behavior patterns.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start the server
uvicorn main:app --app-dir . --reload --port 8000
```

The API will be available at `http://localhost:8000`. The main endpoint is `POST /decide`.

> **Note:** You can provide your OpenAI API key directly in the frontend UI (LLM Settings panel). Alternatively, you can set it as an environment variable (`export OPENAI_API_KEY="sk-..."`) as a fallback — the frontend-provided key takes priority.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173` (default Vite port).

### Running Tests

```bash
cd backend
pytest
```

---

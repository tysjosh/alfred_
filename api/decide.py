"""Vercel serverless function wrapping the FastAPI /decide endpoint."""

import sys
import os

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio

from context_builder import ContextBuilder
from decision_engine import DecisionEngine
from failure_handler import FailureHandler
from models import (
    AllSignals,
    DecideRequest,
    DecideResponse,
    DeterministicSignals,
    LLMSignals,
    RiskLevel,
)
from prompt_builder import PromptBuilder
from signal_extractor import LLMExtractionError, SignalExtractor
from decision_engine import DecisionResult

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM_TIMEOUT_SECONDS = 10


def _build_fallback_response(
    fallback_result: DecisionResult,
    deterministic: DeterministicSignals,
    prompt_text: str,
) -> DecideResponse:
    fallback_llm = LLMSignals(
        intent_clarity=0.0,
        risk_level=RiskLevel.LOW,
        consistency_with_history=False,
        ambiguity_detected=False,
        policy_violation=False,
    )
    return DecideResponse(
        decision=fallback_result.decision,
        confidence_score=fallback_result.confidence_score,
        signals=AllSignals(deterministic=deterministic, llm=fallback_llm),
        explanation=fallback_result.explanation,
        why_not_others=fallback_result.why_not_others,
        fallback_reason=fallback_result.fallback_reason,
        raw_llm_response=None,
        prompt_text=prompt_text,
    )


@app.post("/api/decide")
async def decide(request: DecideRequest) -> DecideResponse:
    """Evaluate an action and return a decision with reasoning."""
    context_builder = ContextBuilder()
    signal_extractor = SignalExtractor()
    prompt_builder = PromptBuilder()
    decision_engine = DecisionEngine()
    failure_handler = FailureHandler()

    context = context_builder.build(
        action=request.action,
        conversation_history=request.conversation_history,
        user_profile=request.user_profile,
    )

    deterministic = signal_extractor.extract_deterministic(context)
    prompt_text = prompt_builder.build(context, deterministic)
    action_id = f"{request.action.type}:{id(request)}"

    if request.action.type == "failure_demo":
        fallback_result = failure_handler.handle("llm_timeout", action_id, context)
        return _build_fallback_response(fallback_result, deterministic, prompt_text)

    if not context.conversation_history:
        fallback_result = failure_handler.handle("insufficient_context", action_id, context)
        return _build_fallback_response(fallback_result, deterministic, prompt_text)

    raw_llm_response: str | None = None
    try:
        llm_signals, raw_llm_response = await asyncio.wait_for(
            asyncio.to_thread(
                signal_extractor.extract_llm_with_raw,
                context,
                deterministic,
                api_key=request.openai_api_key,
                model=request.openai_model,
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        fallback_result = failure_handler.handle("llm_timeout", action_id, context)
        return _build_fallback_response(fallback_result, deterministic, prompt_text)
    except LLMExtractionError:
        fallback_result = failure_handler.handle("malformed_response", action_id, context)
        return _build_fallback_response(fallback_result, deterministic, prompt_text)
    except Exception:
        fallback_result = failure_handler.handle("llm_error", action_id, context)
        return _build_fallback_response(fallback_result, deterministic, prompt_text)

    all_signals = AllSignals(deterministic=deterministic, llm=llm_signals)
    result = decision_engine.decide(all_signals)

    return DecideResponse(
        decision=result.decision,
        confidence_score=result.confidence_score,
        signals=all_signals,
        explanation=result.explanation,
        why_not_others=result.why_not_others,
        fallback_reason=result.fallback_reason,
        raw_llm_response=raw_llm_response,
        prompt_text=prompt_text,
    )

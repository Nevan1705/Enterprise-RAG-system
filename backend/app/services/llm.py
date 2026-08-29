"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/llm.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Resilient Multi-Tier Large Language Model (LLM) Service.
              Architecture:
                - PRIMARY  : High-Throughput Direct Groq Cloud LPU API
                - RETRIES  : Exponential backoff on transient errors (429, timeouts, 5xx)
                - FALLBACK : LlamaIndex secondary orchestrator failover wrapper
              Enforces strict anti-hallucination system prompt guardrails.
================================================================================
"""
import time
from dataclasses import dataclass
from typing import Optional

import app.core.ssl_patch  # noqa: F401 - Apply SSL fix for Groq and LlamaIndex
from app.core.config import settings
from app.core.logger import setup_logger

# Initialize module logger
logger = setup_logger(__name__)

# -----------------------------------------------------------------------------
# Anti-Hallucination Enterprise System Prompt
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You MUST answer ONLY using the provided context.\n"
    "If the answer is not present, say: 'Not found in provided documents'.\n"
    "Do NOT hallucinate.\n"
    "Provide a highly detailed, comprehensive, and heavily explained answer to the user's question. Elaborate extensively using all relevant information from the context.\n"
    "Do NOT include any citations, source names, or document filenames in your response text. The UI already handles citations automatically."
)


# -----------------------------------------------------------------------------
# LLM Response Data Container
# -----------------------------------------------------------------------------
@dataclass
class LLMResult:
    """Encapsulates the response text, active provider, retry metrics, and latency."""
    answer: str
    provider: str               # "groq" | "llamaindex"
    retries: int
    latency_ms: float
    fallback_triggered: bool


# -----------------------------------------------------------------------------
# 1. Primary Provider: Direct Groq Cloud API
# -----------------------------------------------------------------------------
def _call_groq(
    context: str,
    question: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Invokes Groq API via native client with low-latency inference.
    """
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY, timeout=settings.LLM_TIMEOUT)
    sys_prompt = system_prompt or SYSTEM_PROMPT
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    
    kwargs = {
        "model": settings.GROQ_MODEL,
        "temperature": temp,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
        
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


# -----------------------------------------------------------------------------
# 2. Secondary Provider: LlamaIndex Fallback Orchestrator
# -----------------------------------------------------------------------------
def _call_llamaindex(
    context: str,
    question: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Invoked when primary Groq client fails or exceeds quota.
    Wraps model inference through LlamaIndex abstraction layer.
    """
    sys_prompt = system_prompt or SYSTEM_PROMPT
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE

    try:
        from llama_index.llms.groq import Groq as LlamaGroq  # type: ignore
        from llama_index.core.llms import ChatMessage as LlamaChatMessage  # type: ignore

        api_key = settings.LLAMAINDEX_API_KEY or settings.GROQ_API_KEY
        llm_kwargs = {
            "model": settings.LLAMAINDEX_MODEL,
            "api_key": api_key,
            "temperature": temp,
        }
        if max_tokens is not None:
            llm_kwargs["max_tokens"] = max_tokens
            
        llm = LlamaGroq(**llm_kwargs)

        messages = [
            LlamaChatMessage(role="system", content=sys_prompt),
            LlamaChatMessage(
                role="user",
                content=f"Context:\n{context}\n\nQuestion: {question}",
            ),
        ]
        response = llm.chat(messages)
        return str(response.message.content)

    except ImportError:
        # OpenAI-compatible alternative fallback
        logger.warning("[LLM] llama_index.llms.groq not available, falling back to llama_index.llms.openai_like")
        from llama_index.llms.openai_like import OpenAILike  # type: ignore
        from llama_index.core.llms import ChatMessage as LlamaChatMessage  # type: ignore

        api_key = settings.LLAMAINDEX_API_KEY or settings.GROQ_API_KEY
        llm_kwargs = {
            "model": settings.LLAMAINDEX_MODEL,
            "api_base": "https://api.groq.com/openai/v1",
            "api_key": api_key,
            "is_chat_model": True,
            "temperature": temp,
        }
        if max_tokens is not None:
            llm_kwargs["max_tokens"] = max_tokens
            
        llm = OpenAILike(**llm_kwargs)
        messages = [
            LlamaChatMessage(role="system", content=sys_prompt),
            LlamaChatMessage(
                role="user",
                content=f"Context:\n{context}\n\nQuestion: {question}",
            ),
        ]
        response = llm.chat(messages)
        return str(response.message.content)


# -----------------------------------------------------------------------------
# 3. Public LLM Service Singleton & Failover Engine
# -----------------------------------------------------------------------------
class LLMService:
    """
    Central orchestration service for all generative language modeling tasks.
    Manages retry loops, exponential backoff, failover routing, and telemetry.
    """

    @staticmethod
    def generate(
        context: str,
        question: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        """
        Executes generation with automatic multi-tier failover.
        
        Args:
            context (str): Retrieved context documents.
            question (str): User question or task instruction.
            system_prompt (Optional[str]): Custom system prompt override.
            temperature (Optional[float]): Model sampling temperature.
            max_tokens (Optional[int]): Upper limit on generated tokens.
            
        Returns:
            LLMResult: Generated answer with provider attribution and telemetry metrics.
        """
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured in settings or environment")

        start = time.monotonic()
        retries = 0
        last_exc: Optional[Exception] = None

        # -- Stage 1: Primary Groq with Exponential Backoff Retries --
        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            try:
                logger.info(f"[LLM] GROQ invocation attempt {attempt + 1}/{settings.LLM_MAX_RETRIES + 1}")
                answer = _call_groq(
                    context, 
                    question, 
                    system_prompt=system_prompt, 
                    temperature=temperature, 
                    max_tokens=max_tokens
                )

                latency = (time.monotonic() - start) * 1000
                logger.info(f"[LLM] GROQ success | attempt={attempt + 1} latency={latency:.0f}ms")
                return LLMResult(
                    answer=answer,
                    provider="groq",
                    retries=retries,
                    latency_ms=latency,
                    fallback_triggered=False,
                )
            except Exception as exc:
                retries += 1
                last_exc = exc
                exc_type = type(exc).__name__
                logger.warning(f"[LLM] GROQ attempt {attempt + 1} failed: {exc_type}: {str(exc)[:120]}")
                
                # Check if error is transient and retryable
                if not _is_transient(exc):
                    break
                if attempt < settings.LLM_MAX_RETRIES:
                    time.sleep(1.5 ** attempt)   # Exponential backoff delay

        # -- Stage 2: Trigger LlamaIndex Fallback --
        logger.warning(
            f"[LLM] GROQ primary exhausted after {retries} attempt(s). "
            f"Triggering LlamaIndex fallback. Last error: {last_exc}"
        )
        try:
            answer = _call_llamaindex(
                context, 
                question, 
                system_prompt=system_prompt, 
                temperature=temperature, 
                max_tokens=max_tokens
            )
            latency = (time.monotonic() - start) * 1000
            logger.info(f"[LLM] LlamaIndex fallback SUCCESS | latency={latency:.0f}ms")
            return LLMResult(
                answer=answer,
                provider="llamaindex",
                retries=retries,
                latency_ms=latency,
                fallback_triggered=True,
            )
        except Exception as fb_exc:
            latency = (time.monotonic() - start) * 1000
            logger.error(f"[LLM] LlamaIndex fallback FAILED: {fb_exc}")
            raise RuntimeError(
                f"Both Primary (Groq) and Fallback (LlamaIndex) failed. "
                f"Last Groq error: {last_exc}. LlamaIndex error: {fb_exc}"
            )


# -----------------------------------------------------------------------------
# Transient Error Classification
# -----------------------------------------------------------------------------
def _is_transient(exc: Exception) -> bool:
    """
    Identifies transient network or rate-limiting errors suitable for retry.
    """
    exc_name = type(exc).__name__.lower()
    transient_keywords = ["timeout", "ratelimit", "rate_limit", "connection", "503", "502", "500"]
    return any(k in exc_name for k in transient_keywords) or any(
        k in str(exc).lower() for k in ["timeout", "rate limit", "connection", "503", "502"]
    )

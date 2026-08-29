"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/testcase_service.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Multi-Batch Enterprise QA Test Case Generation Engine.
              - Detects QA testing intent from user queries
              - Partitions generation into 4 dedicated scenario categories:
                  1. Functional happy path scenarios
                  2. Negative and error handling scenarios
                  3. Edge and boundary scenarios
                  4. Security, authentication, authorization, and concurrency
              - Implements resilient JSON self-healing and bracket-depth extraction
              - Enforces Pydantic schema validation (TestCaseItem) and ID renumbering
================================================================================
"""
import json
import re
from typing import List
from pydantic import ValidationError

import app.core.ssl_patch  # noqa: F401 - Apply SSL fix for Groq and LlamaIndex
from app.models.schemas import TestCaseItem
from app.services.llm import LLMService
from app.core.logger import setup_logger

# Initialize module logger
logger = setup_logger(__name__)

# -----------------------------------------------------------------------------
# Configuration Constants & Partition Categories
# -----------------------------------------------------------------------------
_CONTEXT_CHAR_LIMIT = 5000
_QUESTION_CHAR_LIMIT = 1500
_BATCH_MAX_TOKENS = 3500
_CASES_PER_BATCH = 5

_CATEGORY_BATCHES = [
    "Functional happy path scenarios",
    "Negative and error handling scenarios",
    "Edge and boundary scenarios",
    "Security, authentication, authorization, and concurrency scenarios",
]

_SIZE_ERROR_MARKERS = (
    "request too large",
    "context length",
    "maximum context length",
    "token limit",
    "too many tokens",
)

# Strict QA Engineer System Prompt
TESTCASE_SYSTEM_PROMPT = """You are a Lead Enterprise Quality Assurance (QA) Engineer.
Your objective is to analyze the provided context and generate structured test cases.

You MUST output ONLY valid JSON.
DO NOT wrap the JSON in Markdown formatting (no ```json ... ```).
DO NOT output any explanations, reasoning, or conversational text.
The JSON MUST be a list of objects matching this exact structure:
[
  {
    "test_case_id": "TC_001",
    "requirement_id": "REQ_001",
    "test_scenario": "...",
    "test_case_description": "...",
    "preconditions": "...",
    "test_steps": [
      "Step 1...",
      "Step 2..."
    ],
    "test_data": "...",
    "expected_result": "..."
  }
]
"""


# -----------------------------------------------------------------------------
# 1. Intent Detection & Context Slicing
# -----------------------------------------------------------------------------
def is_testcase_request(question: str) -> bool:
    """
    Determines if user input contains QA testcase generation intent.
    """
    keywords = [
        "generate test case", "generate testcase", "test cases", "testcase",
        "test scenario", "qa scenario", "functional test", "negative test",
        "boundary test", "export testcases"
    ]
    q_lower = question.lower()
    return any(kw in q_lower for kw in keywords)


def _fit_context(context: str, max_chars: int) -> str:
    """Safely truncates context to avoid model token exhaustion."""
    if len(context) <= max_chars:
        return context
    return (
        context[:max_chars]
        + "\n\n[Context truncated to fit model input limits while preserving top-retrieval chunks.]"
    )


def _fit_question(question: str, max_chars: int) -> str:
    """Truncates question to maximum bounds."""
    if len(question) <= max_chars:
        return question
    return (
        question[:max_chars]
        + "\n\n[Question truncated to fit model input limits.]"
    )


def _is_size_error(exc: Exception) -> bool:
    """Identifies token or payload size errors."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _SIZE_ERROR_MARKERS)


def _clean_json_string(answer: str) -> str:
    """Strips Markdown code blocks from LLM raw response."""
    answer = answer.strip()
    if answer.startswith("```json"):
        answer = answer[7:]
    elif answer.startswith("```"):
        answer = answer[3:]
    if answer.endswith("```"):
        answer = answer[:-3]
    return answer.strip()


# -----------------------------------------------------------------------------
# 2. Resilient JSON Extraction & Self-Healing Parser
# -----------------------------------------------------------------------------
def _extract_json_objects(text: str) -> list[dict]:
    """
    Robust JSON parser that extracts objects using multi-stage recovery:
      1. Direct json.loads parsing
      2. Outer bracket slicing [ ... ]
      3. Partial array recovery with bracket closure
      4. Character-by-character brace matching depth algorithm { ... }
    """
    text = _clean_json_string(text)
    
    # 1. Direct parse attempt
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
    except Exception:
        pass

    # 2. Extract substring between '[' and ']'
    start_bracket = text.find('[')
    if start_bracket != -1:
        end_bracket = text.rfind(']')
        if end_bracket != -1 and end_bracket > start_bracket:
            try:
                data = json.loads(text[start_bracket:end_bracket + 1])
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
            except Exception:
                pass
        
        # Truncated array: find last '}' and close bracket
        last_brace = text.rfind('}')
        if last_brace != -1 and last_brace > start_bracket:
            sub = text[start_bracket:last_brace + 1].strip()
            if sub.endswith(','):
                sub = sub[:-1]
            try:
                data = json.loads(sub + ']')
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
            except Exception:
                pass

    # 3. Individual brace-matching state machine
    items: list[dict] = []
    pos = 0
    while pos < len(text):
        start = text.find('{', pos)
        if start == -1:
            break
        depth = 0
        in_string = False
        escape = False
        end = -1
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end != -1:
            chunk = text[start:end + 1]
            try:
                obj = json.loads(chunk)
                if isinstance(obj, dict):
                    items.append(obj)
            except Exception:
                pass
            pos = end + 1
        else:
            pos = start + 1

    return items


# -----------------------------------------------------------------------------
# 3. Pydantic Schema Validation & Deduplication
# -----------------------------------------------------------------------------
def _validate_testcase_items(raw_items: List[dict]) -> List[dict]:
    """Validates raw dicts against TestCaseItem schema and normalizes types."""
    validated = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        try:
            # Enforce string type for test_data
            if 'test_data' in item and not isinstance(item['test_data'], str):
                item['test_data'] = json.dumps(item['test_data'])
            # Enforce list of strings for test_steps
            if 'test_steps' in item:
                if isinstance(item['test_steps'], str):
                    item['test_steps'] = [item['test_steps']]
                elif not isinstance(item['test_steps'], list):
                    item['test_steps'] = [str(item['test_steps'])]
                else:
                    item['test_steps'] = [str(s) for s in item['test_steps']]
            else:
                item['test_steps'] = ["Execute test scenario"]

            valid_item = TestCaseItem(**item)
            validated.append(valid_item.model_dump())
        except (ValidationError, Exception) as val_err:
            logger.debug(f"[TESTCASE] Item validation skipped malformed entry: {val_err}")
            continue

    return validated


def _renumber_testcases(items: List[dict]) -> List[dict]:
    """Assigns sequential standard test IDs (TC_001, TC_002, etc.)."""
    for i, item in enumerate(items, start=1):
        item["test_case_id"] = f"TC_{i:03d}"
        if not item.get("requirement_id"):
            item["requirement_id"] = "REQ_001"
    return items


def _dedupe_testcases(items: List[dict]) -> List[dict]:
    """Eliminates duplicate testcases across batches."""
    seen = set()
    unique = []
    for item in items:
        key = (
            item.get("test_scenario", "").strip().lower(),
            item.get("expected_result", "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


# -----------------------------------------------------------------------------
# 4. Multi-Batch Generation Pipeline
# -----------------------------------------------------------------------------
def generate_testcases_json(context: str, question: str) -> tuple[List[dict], str]:
    """
    Orchestrates multi-batch QA test case generation across all 4 categories.
    
    Args:
        context (str): Retrieved document context.
        question (str): User prompt instructions.
        
    Returns:
        tuple[List[dict], str]: (Validated testcase list, Active LLM provider name).
    """
    compact_context = _fit_context(context, _CONTEXT_CHAR_LIMIT)
    compact_question = _fit_question(question, _QUESTION_CHAR_LIMIT)

    all_items: List[dict] = []
    provider_used = "groq"
    last_error: Exception | None = None

    # Execute category-specific generation batches
    for category in _CATEGORY_BATCHES:
        batch_question = (
            f"{compact_question}\n\n"
            f"Generate {_CASES_PER_BATCH} testcases for this category: {category}. "
            "Output ONLY a valid JSON array of test cases."
        )

        try:
            result = LLMService.generate(
                context=compact_context,
                question=batch_question,
                system_prompt=TESTCASE_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=_BATCH_MAX_TOKENS,
            )
            provider_used = result.provider
            raw_objects = _extract_json_objects(result.answer)
            validated = _validate_testcase_items(raw_objects)
            if validated:
                all_items.extend(validated)
                logger.info(f"[TESTCASE] Generated {len(validated)} test cases for category '{category}'")
            else:
                logger.warning(f"[TESTCASE] No valid test case objects parsed for category '{category}'")
        except Exception as exc:
            last_error = exc
            logger.warning(f"[TESTCASE] Batch error for category '{category}': {exc}")
            if _is_size_error(exc):
                continue
            continue

    all_items = _dedupe_testcases(all_items)
    all_items = _renumber_testcases(all_items)

    if all_items:
        logger.info(f"[TESTCASE] Successfully generated total {len(all_items)} validated test cases.")
        return all_items, provider_used

    # Single-batch fallback if all individual batches returned empty
    logger.warning("[TESTCASE] Batched attempts yielded 0 cases. Attempting single-batch fallback.")
    try:
        fallback_prompt = (
            f"{compact_question}\n\n"
            "Generate at least 5 comprehensive test cases covering positive, negative, and edge scenarios. "
            "Output ONLY a valid JSON array."
        )
        result = LLMService.generate(
            context=compact_context,
            question=fallback_prompt,
            system_prompt=TESTCASE_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=_BATCH_MAX_TOKENS,
        )
        provider_used = result.provider
        raw_objects = _extract_json_objects(result.answer)
        validated = _validate_testcase_items(raw_objects)
        validated = _dedupe_testcases(validated)
        validated = _renumber_testcases(validated)
        if validated:
            return validated, provider_used
    except Exception as exc:
        last_error = exc

    if last_error is None:
        raise ValueError("No testcases could be extracted from model response.")
    raise ValueError(f"Failed to generate valid testcases: {str(last_error)}")

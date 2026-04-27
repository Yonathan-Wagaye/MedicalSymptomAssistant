"""
OpenAI LLM service for the Medical Symptom Assistant.

Wraps the chat-completions API with:
  - a medical-assistant system prompt with tiered response policies
  - JSON-mode output for structured responses
  - conversation-history support for multi-turn sessions
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from backend.core.config import config

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

SYSTEM_PROMPT = """\
You are a medical information assistant.  You provide general health \
information based on retrieved medical sources.  You are NOT a doctor \
and cannot diagnose, prescribe, or triage.

══ RESPONSE POLICIES ══

POLICY 1 — VAGUE / UNDERSPECIFIED QUERIES
When the user's input lacks specific symptoms (e.g. "I don't feel well", \
"I feel sick", "something is wrong"):
  • Do NOT list diseases or conditions.
  • Acknowledge their concern empathetically.
  • Ask 2–3 targeted follow-up questions, for example:
    – What specific symptoms are you experiencing (pain, fever, nausea, \
      dizziness, etc.)?
    – When did this start, and how long has it lasted?
    – Is there anything that makes it better or worse?
  • Set urgency to "clarification_needed".
  • Return an empty list for related_conditions.

POLICY 2 — RED-FLAG / EMERGENCY SYMPTOMS
When the query mentions chest pain, difficulty breathing, loss of \
consciousness, severe bleeding, suicidal thoughts, seizures, or \
similar emergency symptoms:
  • FIRST: State clearly that these symptoms may require urgent medical \
    evaluation — advise calling emergency services or visiting an ER.
  • SECOND: Provide brief factual context from the retrieved sources.
  • THIRD: Re-emphasise that professional evaluation is essential.
  • Set urgency to "emergency".
  • Do NOT downplay the symptoms.

POLICY 3 — MODERATE / SPECIFIC QUERIES
When the user describes identifiable symptoms:
  • Summarise what the retrieved sources say about those symptoms.
  • Use cautious language ("may be associated with", "could be related to").
  • Express uncertainty proportional to the evidence — few matches = lower \
    confidence.  Broad/generic matches = prefer symptom categories over \
    specific disease names (e.g. "common in respiratory infections" rather \
    than "you may have pneumonia").
  • Suggest when to seek professional care.
  • Set urgency to "normal".

══ GENERAL RULES ══

1. Ground answers ONLY in the provided context.  If the context does not \
   address the question, say so honestly.
2. Never recommend specific medications or dosages.
3. Prefer broad categories over specific diagnoses when evidence is weak.
4. Always end with a recommendation to consult a healthcare professional.
5. Cite source titles when referencing specific information.

══ RESPONSE FORMAT ══

Reply with a JSON object:
{
  "urgency": "emergency" | "normal" | "clarification_needed",
  "answer": "Your response following the appropriate policy …",
  "follow_up_questions": ["question1", "question2"],
  "related_conditions": [
    {
      "name": "Condition or Category Name",
      "matched_symptoms": ["symptom1", "symptom2"],
      "confidence": "low" | "moderate",
      "explanation": "Brief reason this may be relevant"
    }
  ]
}

Field notes:
  • urgency — "emergency" for red-flag symptoms, "clarification_needed" for \
    vague queries, "normal" otherwise.
  • follow_up_questions — populate for vague queries; empty list otherwise.
  • related_conditions — empty for vague queries.  For moderate queries with \
    thin evidence, set confidence to "low".
  • confidence — "moderate" only when multiple sources corroborate the match; \
    default to "low".\
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set.  Add it to backend/.env"
            )
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def build_context_block(sources: list[dict]) -> str:
    """Format retrieved search results into a numbered context block."""
    if not sources:
        return "(No relevant context was retrieved for this query.)"

    lines: list[str] = []
    for i, src in enumerate(sources, 1):
        title = src.get("title", "Untitled")
        url = src.get("url", "")
        text = src.get("text", "")
        header = f"[{i}] {title}"
        if url:
            header += f"\n    Source: {url}"
        lines.append(f"{header}\n{text}")
    return "\n\n".join(lines)


def chat_completion(
    messages: list[dict[str, str]],
    *,
    json_mode: bool = True,
) -> str:
    """
    Call OpenAI chat completions and return the assistant reply text.

    *messages* should already include the system prompt, any history,
    the context block, and the latest user message.
    """
    client = _get_client()

    kwargs: dict[str, Any] = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": config.LLM_MAX_TOKENS,
        "temperature": config.LLM_TEMPERATURE,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    logger.info("Calling %s (msgs=%d, json=%s) …", config.LLM_MODEL, len(messages), json_mode)
    response = client.chat.completions.create(**kwargs)
    text = response.choices[0].message.content or ""
    logger.info(
        "LLM replied (%d chars, %d prompt + %d completion tokens)",
        len(text),
        response.usage.prompt_tokens if response.usage else 0,
        response.usage.completion_tokens if response.usage else 0,
    )
    return text


def parse_llm_json(raw: str) -> dict:
    """
    Parse the JSON response from the LLM.

    Falls back to wrapping the raw text as {"answer": raw} if parsing
    fails, so the caller always gets a usable dict.
    """
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("LLM response was not valid JSON — using raw text as answer")
        return {
            "urgency": "normal",
            "answer": raw,
            "follow_up_questions": [],
            "related_conditions": [],
        }

"""
AI Agent — orchestrates the provider, prompts, and memory service
to produce a contextual reply or analysis for a given conversation.
"""

import json
import logging
from dataclasses import dataclass, field

from app.ai.memory import MemoryService
from app.ai.prompts import (
    OWNER_AWAY_MESSAGE,
    build_categorise_messages,
    format_history,
)
from app.ai.providers import AIProvider

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    user_id: int
    sender_name: str
    latest_message: str
    history: list[dict[str, str]]


@dataclass
class AgentResult:
    draft_reply: str | None
    category: str | None
    priority: str | None
    summary: str | None
    # ── Phase 4 additions ─────────────────────────────────────────────────────
    confidence: float | None = None
    intent: str | None = None
    sentiment: str | None = None
    reasoning: str | None = None
    requires_human_review: bool = False
    extracted_memories: list[dict[str, str]] = field(default_factory=list)


class FiromsaAgent:
    """
    The core AI agent.

    Phase 1: Foundation skeleton.
    Phase 2: Full integration — persist results, draft replies.
    Phase 4: Categorisation call extended to also return confidence/intent/
             sentiment/reasoning/requires_human_review, and to extract
             durable long-term facts (persisted here via MemoryService —
             no separate AI call, no separate extraction pipeline).
    """

    def __init__(self, provider: AIProvider, memory_service: MemoryService) -> None:
        self._provider = provider
        self._memory = memory_service

    async def process(self, ctx: ConversationContext) -> AgentResult:
        logger.info(
            "Agent processing message from %s for user_id=%s",
            ctx.sender_name,
            ctx.user_id,
        )

        history_text = format_history(ctx.history)

        # Fixed professional away/welcome message — used for every incoming
        # message regardless of length or content, instead of an LLM-drafted
        # reply. This guarantees a consistent, reliable response even for
        # short greetings ("hi", "hello") that previously produced no reply
        # at all due to LLM variability.
        draft_reply = OWNER_AWAY_MESSAGE
        logger.debug("Using fixed away-message template (len=%d).", len(draft_reply))

        cat_messages = build_categorise_messages(history_text, ctx.latest_message)
        raw_classification = await self._provider.chat(cat_messages, temperature=0.1)
        data = self._parse_classification(raw_classification)

        confidence = self._safe_float(data.get("confidence"))
        extracted_memories = self._sanitise_memories(data.get("extracted_memories"))

        for mem in extracted_memories:
            await self._memory.store(ctx.user_id, mem["key"], mem["value"])

        return AgentResult(
            draft_reply=draft_reply,
            category=data.get("category"),
            priority=data.get("priority"),
            summary=data.get("summary"),
            confidence=confidence,
            intent=data.get("intent"),
            sentiment=data.get("sentiment"),
            reasoning=data.get("reasoning"),
            requires_human_review=bool(data.get("requires_human_review", False)),
            extracted_memories=extracted_memories,
        )

    @staticmethod
    def _parse_classification(raw: str) -> dict:
        """
        Parse JSON even if the LLM wraps it with explanations or markdown
        code fences (``` or ```json). Locating the outermost { ... } braces
        is more robust than trying to strip fence markers by string prefix,
        since the LLM doesn't always tag the fence with "json".
        """
        if not raw:
            return {}
        try:
            cleaned = raw.strip()

            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end + 1]

            data = json.loads(cleaned)
            return data if isinstance(data, dict) else {}
        except Exception:
            logger.exception("Failed to parse classification JSON")
            logger.error("RAW RESPONSE:\n%s", raw)
            return {}

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sanitise_memories(raw) -> list[dict[str, str]]:
        if not isinstance(raw, list):
            return []
        cleaned: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            value = item.get("value")
            if key and value:
                cleaned.append({"key": str(key), "value": str(value)})
        return cleaned

"""
AI Agent — orchestrates the provider, prompts, and memory service
to produce a contextual reply or analysis for a given conversation.
"""

import json
import logging
from dataclasses import dataclass

from app.ai.memory import MemoryService
from app.ai.prompts import (
    build_categorise_messages,
    build_draft_reply_messages,
    format_history,
)
from app.ai.providers import AIProvider

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Minimal context object passed to the agent for a single run."""

    user_id: int
    sender_name: str
    latest_message: str
    history: list[dict[str, str]]  # [{"sender": "owner"|"contact"|"ai", "content": "..."}]


@dataclass
class AgentResult:
    draft_reply: str | None
    category: str | None
    priority: str | None
    summary: str | None


class FiromsaAgent:
    """
    The core AI agent.

    Phase 1: Foundation skeleton — methods are wired up but return
             graceful placeholders until the Telegram handler calls them.
    Phase 2: Full integration — persist results, trigger auto-replies,
             update memory after each interaction.
    """

    def __init__(self, provider: AIProvider, memory_service: MemoryService) -> None:
        self._provider = provider
        self._memory = memory_service

    async def process(self, ctx: ConversationContext) -> AgentResult:
        """
        Full agent pipeline for an incoming message:
        1. Retrieve relevant memories for the user.
        2. Build a draft reply.
        3. Categorise the conversation.
        4. Return structured results.
        """
        logger.info(
            "Agent processing message from %s for user_id=%s",
            ctx.sender_name,
            ctx.user_id,
        )

        # 1. Retrieve memories
        memories_text = await self._memory.retrieve_formatted(ctx.user_id)

        # 2. Draft reply
        history_text = format_history(ctx.history)
        reply_messages = build_draft_reply_messages(
            history=history_text,
            sender=ctx.sender_name,
            latest_message=ctx.latest_message,
            memories=memories_text,
        )
        draft_reply = await self._provider.chat(reply_messages, temperature=0.6)
        logger.debug("Draft reply generated (len=%d).", len(draft_reply))

        # 3. Categorise
        cat_messages = build_categorise_messages(history_text)
        raw_classification = await self._provider.chat(cat_messages, temperature=0.1)
        category, priority, summary = self._parse_classification(raw_classification)

        return AgentResult(
            draft_reply=draft_reply,
            category=category,
            priority=priority,
            summary=summary,
        )

    @staticmethod
    def _parse_classification(
        raw: str,
    ) -> tuple[str | None, str | None, str | None]:
        """
        Parse the JSON classification response from the model.
        Returns (category, priority, summary) or (None, None, None) on error.
        """
        try:
            # Strip potential markdown fencing
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(cleaned)
            return (
                data.get("category"),
                data.get("priority"),
                data.get("summary"),
            )
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("Failed to parse classification JSON: %s | raw=%r", exc, raw[:200])
            return None, None, None

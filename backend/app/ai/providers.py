"""
AI provider abstraction layer.

Supports OpenAI and Groq (both are OpenAI API-compatible).
The active provider is selected via the AI_PROVIDER environment variable.
Adding a new provider only requires implementing AIProvider and registering
it in the factory below — no changes elsewhere in the codebase.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


# ── Provider interface ────────────────────────────────────────────────────────

class AIProvider(ABC):
    """Abstract base for all AI provider implementations."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send a list of chat messages and return the assistant reply as a string.

        Args:
            messages: OpenAI-format messages, e.g.
                      [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            temperature: Sampling temperature (0 = deterministic, 1 = creative).
            max_tokens: Maximum tokens in the completion.

        Returns:
            The assistant's reply text.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name for logging."""


# ── OpenAI implementation ─────────────────────────────────────────────────────

class OpenAIProvider(AIProvider):
    """Provider backed by the OpenAI API (or any OpenAI-compatible endpoint)."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._model = settings.openai_model

    @property
    def provider_name(self) -> str:
        return f"openai/{self._model}"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        logger.debug("OpenAI request: model=%s messages=%d", self._model, len(messages))
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


# ── Groq implementation ───────────────────────────────────────────────────────

class GroqProvider(AIProvider):
    """
    Provider backed by Groq (OpenAI-compatible endpoint).
    Uses the openai SDK pointed at api.groq.com.
    """

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when AI_PROVIDER=groq")
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
        self._model = settings.groq_model

    @property
    def provider_name(self) -> str:
        return f"groq/{self._model}"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        logger.debug("Groq request: model=%s messages=%d", self._model, len(messages))
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


# ── Factory ───────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
}

_provider_instance: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    """
    FastAPI dependency / singleton factory.
    Instantiated once and reused for the lifetime of the process.
    """
    global _provider_instance
    if _provider_instance is None:
        name = settings.ai_provider
        provider_cls = _PROVIDERS.get(name)
        if provider_cls is None:
            raise ValueError(
                f"Unknown AI_PROVIDER '{name}'. "
                f"Choose one of: {', '.join(_PROVIDERS)}"
            )
        _provider_instance = provider_cls()
        logger.info("AI provider initialised: %s", _provider_instance.provider_name)
    return _provider_instance

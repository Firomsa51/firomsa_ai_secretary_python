"""
AI provider abstraction layer.

Supports OpenAI, Groq, and Gemini (all OpenAI API-compatible endpoints).
A FallbackAIProvider wraps multiple providers and automatically moves to
the next one if a call fails — e.g. when Groq's free-tier rate limit is
hit, it transparently retries with Gemini instead of failing the whole
request. The fallback order is configured via AI_PROVIDER_FALLBACK_ORDER.

Adding a new provider only requires implementing AIProvider, registering
it in _PROVIDERS below, and adding it to the fallback order env var —
no changes elsewhere in the codebase.
"""

import logging
from abc import ABC, abstractmethod

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


# ── Shared OpenAI-compatible implementation ────────────────────────────────────

class _OpenAICompatibleProvider(AIProvider):
    """
    Base class for any OpenAI-API-compatible provider (OpenAI itself,
    Groq, Gemini's OpenAI-compat endpoint, etc). Subclasses just supply
    api_key / base_url / model.
    """

    def __init__(self, *, label: str, api_key: str, base_url: str, model: str) -> None:
        self._label = label
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    @property
    def provider_name(self) -> str:
        return f"{self._label}/{self._model}"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        logger.debug("%s request: model=%s messages=%d", self._label, self._model, len(messages))
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


class OpenAIProvider(_OpenAICompatibleProvider):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        super().__init__(
            label="openai",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )


class GroqProvider(_OpenAICompatibleProvider):
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        super().__init__(
            label="groq",
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_model,
        )


class GeminiProvider(_OpenAICompatibleProvider):
    """Google Gemini via its OpenAI-compatible endpoint. Free tier at aistudio.google.com."""

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        super().__init__(
            label="gemini",
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=settings.gemini_model,
        )


# ── Fallback wrapper ────────────────────────────────────────────────────────

class FallbackAIProvider(AIProvider):
    """
    Wraps multiple AIProvider instances and tries them in order. If a
    provider's call raises (rate limit, quota exceeded, network error,
    invalid response, etc.), the error is logged and the next provider in
    the list is tried automatically. Only fails the whole request if every
    provider in the chain fails.
    """

    def __init__(self, providers: list[AIProvider]) -> None:
        if not providers:
            raise ValueError("FallbackAIProvider requires at least one provider")
        self._providers = providers

    @property
    def provider_name(self) -> str:
        return "fallback[" + ", ".join(p.provider_name for p in self._providers) + "]"

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                result = await provider.chat(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
                logger.debug("AI call succeeded via %s", provider.provider_name)
                return result
            except Exception as exc:  # noqa: BLE001 — intentionally broad: any failure triggers fallback
                last_error = exc
                logger.warning(
                    "AI provider %s failed (%s: %s) — trying next provider.",
                    provider.provider_name, type(exc).__name__, exc,
                )
        logger.error("All AI providers failed. Last error: %s", last_error)
        raise last_error or RuntimeError("All AI providers failed with no recorded error")


# ── Factory ───────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "gemini": GeminiProvider,
}

_provider_instance: AIProvider | None = None


def _build_provider(name: str) -> AIProvider | None:
    """Build a single named provider, returning None if not configured/available."""
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        logger.warning("Unknown provider name %r in fallback order — skipping.", name)
        return None
    try:
        return provider_cls()
    except ValueError as exc:
        logger.info("Provider %r not configured, skipping (%s).", name, exc)
        return None


def get_ai_provider() -> AIProvider:
    """
    FastAPI dependency / singleton factory.
    Instantiated once and reused for the lifetime of the process.

    Builds every provider listed in AI_PROVIDER_FALLBACK_ORDER whose API
    key is actually configured, in that order, and wraps them in a
    FallbackAIProvider. If only one provider ends up configured, it is
    used directly (still safe/simple). Falls back to the single
    AI_PROVIDER setting if the fallback order yields nothing usable.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    order = [name.strip().lower() for name in settings.ai_provider_fallback_order.split(",") if name.strip()]
    built: list[AIProvider] = []
    for name in order:
        provider = _build_provider(name)
        if provider is not None:
            built.append(provider)

    if not built:
        # Fallback to the single configured provider as a last resort.
        provider = _build_provider(settings.ai_provider)
        if provider is None:
            raise ValueError(
                "No AI provider is configured. Set at least one of "
                "GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY."
            )
        built = [provider]

    _provider_instance = built[0] if len(built) == 1 else FallbackAIProvider(built)
    logger.info("AI provider initialised: %s", _provider_instance.provider_name)
    return _provider_instance

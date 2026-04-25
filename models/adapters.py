"""Model adapter layer for the evaluation harness.

Provides an abstract ModelAdapter interface and concrete implementations.
Ships with AnthropicAdapter; other providers extend the same interface.
"""

from __future__ import annotations

import asyncio
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    """Response from a model adapter."""

    text: str
    model_id: str
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    raw_response: Any = None


class ModelAdapter(ABC):
    """Abstract base class for model adapters."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: dict | None = None,
    ) -> ModelResponse:
        ...

    def batch_generate(
        self,
        prompts: list[str],
        system_prompt: str | None = None,
        config: dict | None = None,
    ) -> list[ModelResponse]:
        """Default sequential batch implementation. Override for parallelism."""
        return [self.generate(p, system_prompt, config) for p in prompts]


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        api_key: str | None = None,
        concurrency: int = 5,
    ):
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._concurrency = concurrency
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

        import anthropic
        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=self._api_key)

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def model_version(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: dict | None = None,
    ) -> ModelResponse:
        config = config or {}
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": config.get("max_tokens", self._max_tokens),
            "temperature": config.get("temperature", self._temperature),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        start = time.monotonic()
        response = self._client.messages.create(**kwargs)
        latency_ms = (time.monotonic() - start) * 1000

        text = response.content[0].text if response.content else ""
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return ModelResponse(
            text=text,
            model_id=self._model,
            usage=usage,
            latency_ms=latency_ms,
            raw_response=response,
        )

    def batch_generate(
        self,
        prompts: list[str],
        system_prompt: str | None = None,
        config: dict | None = None,
    ) -> list[ModelResponse]:
        """Parallel batch generation using asyncio."""
        return asyncio.run(
            self._async_batch(prompts, system_prompt, config)
        )

    async def _async_batch(
        self,
        prompts: list[str],
        system_prompt: str | None,
        config: dict | None,
    ) -> list[ModelResponse]:
        semaphore = asyncio.Semaphore(self._concurrency)
        tasks = [
            self._async_generate(p, system_prompt, config, semaphore)
            for p in prompts
        ]
        return await asyncio.gather(*tasks)

    async def _async_generate(
        self,
        prompt: str,
        system_prompt: str | None,
        config: dict | None,
        semaphore: asyncio.Semaphore,
    ) -> ModelResponse:
        config = config or {}
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": config.get("max_tokens", self._max_tokens),
            "temperature": config.get("temperature", self._temperature),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        async with semaphore:
            start = time.monotonic()
            response = await self._async_client.messages.create(**kwargs)
            latency_ms = (time.monotonic() - start) * 1000

        text = response.content[0].text if response.content else ""
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return ModelResponse(
            text=text,
            model_id=self._model,
            usage=usage,
            latency_ms=latency_ms,
            raw_response=response,
        )


def create_adapter(provider: str, **kwargs) -> ModelAdapter:
    """Factory function to create model adapters.

    Args:
        provider: Provider name (e.g., "anthropic")
        **kwargs: Provider-specific configuration

    Returns:
        Configured ModelAdapter instance

    Raises:
        NotImplementedError: For unsupported providers
    """
    if provider == "anthropic":
        return AnthropicAdapter(**kwargs)

    raise NotImplementedError(
        f"Provider '{provider}' is not supported. "
        f"To add support, create a new class that extends ModelAdapter "
        f"in models/adapters.py and register it in create_adapter()."
    )

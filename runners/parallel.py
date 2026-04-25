"""Parallel runner for batched model calls with progress reporting."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from models.adapters import ModelAdapter, ModelResponse
from runners.cache import ResponseCache, CachedAdapter


class ParallelRunner:
    """Run batched model calls with configurable concurrency.

    Integrates with ResponseCache to avoid redundant API calls.
    Reports progress to stderr.
    """

    def __init__(
        self,
        adapter: ModelAdapter,
        concurrency: int = 5,
        cache: ResponseCache | None = None,
        show_progress: bool = True,
    ):
        self.concurrency = concurrency
        self.show_progress = show_progress

        if cache is not None:
            self.adapter = CachedAdapter(adapter, cache)
        else:
            self.adapter = adapter

    def run_batch(
        self,
        prompts: list[str],
        system_prompt: str | None = None,
        config: dict | None = None,
    ) -> list[ModelResponse]:
        """Run a batch of prompts with concurrency control.

        Args:
            prompts: List of prompts to process.
            system_prompt: Optional system prompt for all calls.
            config: Optional generation config.

        Returns:
            List of ModelResponse objects in the same order as prompts.
        """
        return asyncio.run(
            self._run_async(prompts, system_prompt, config)
        )

    async def _run_async(
        self,
        prompts: list[str],
        system_prompt: str | None,
        config: dict | None,
    ) -> list[ModelResponse]:
        semaphore = asyncio.Semaphore(self.concurrency)
        completed = 0
        total = len(prompts)
        results: list[ModelResponse | None] = [None] * total

        async def process(idx: int, prompt: str) -> None:
            nonlocal completed
            async with semaphore:
                # Run in thread pool since adapter.generate is sync
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.adapter.generate(prompt, system_prompt, config)
                )
                results[idx] = response
                completed += 1
                if self.show_progress:
                    print(f"\r  Progress: {completed}/{total}", end="", file=sys.stderr)

        tasks = [process(i, p) for i, p in enumerate(prompts)]
        await asyncio.gather(*tasks)

        if self.show_progress:
            print(file=sys.stderr)  # newline after progress

        return [r for r in results if r is not None]

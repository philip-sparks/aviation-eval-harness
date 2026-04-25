"""Response caching layer for reproducibility.

SQLite-backed cache keyed on model_id + model_version + prompt_hash + config_hash.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from models.adapters import ModelResponse


DEFAULT_CACHE_DIR = Path(".eval_cache")
DEFAULT_DB_NAME = "responses.db"


class ResponseCache:
    """SQLite-backed response cache for model outputs."""

    def __init__(self, cache_dir: Path | str | None = None):
        cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = cache_dir / DEFAULT_DB_NAME
        self._conn = sqlite3.connect(str(self._db_path))
        self._init_db()
        self._hits = 0
        self._misses = 0

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                cache_key TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                response_text TEXT NOT NULL,
                usage_json TEXT,
                latency_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    @staticmethod
    def make_key(
        model_id: str,
        model_version: str,
        prompt: str,
        config: dict | None = None,
    ) -> str:
        """Create a cache key from model + prompt + config."""
        config_str = json.dumps(config or {}, sort_keys=True)
        raw = f"{model_id}:{model_version}:{prompt}:{config_str}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> ModelResponse | None:
        """Retrieve a cached response."""
        cursor = self._conn.execute(
            "SELECT response_text, model_id, usage_json, latency_ms FROM responses WHERE cache_key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            self._misses += 1
            return None

        self._hits += 1
        usage = json.loads(row[2]) if row[2] else {}
        return ModelResponse(
            text=row[0],
            model_id=row[1],
            usage=usage,
            latency_ms=row[3] or 0.0,
        )

    def put(self, key: str, response: ModelResponse, model_version: str = "", prompt: str = "") -> None:
        """Store a response in the cache."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest() if prompt else ""
        self._conn.execute(
            """INSERT OR REPLACE INTO responses
               (cache_key, model_id, model_version, prompt_hash, response_text, usage_json, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                key,
                response.model_id,
                model_version,
                prompt_hash,
                response.text,
                json.dumps(response.usage),
                response.latency_ms,
            ),
        )
        self._conn.commit()

    def invalidate(self, model_version: str) -> int:
        """Remove all entries for a specific model version."""
        cursor = self._conn.execute(
            "DELETE FROM responses WHERE model_version = ?",
            (model_version,),
        )
        self._conn.commit()
        return cursor.rowcount

    def stats(self) -> dict:
        """Return cache statistics."""
        cursor = self._conn.execute("SELECT COUNT(*) FROM responses")
        total = cursor.fetchone()[0]
        return {
            "total_entries": total,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0,
            "db_path": str(self._db_path),
        }

    def clear(self) -> None:
        """Clear all cached responses."""
        self._conn.execute("DELETE FROM responses")
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


class CachedAdapter:
    """Wrapper that adds caching to any ModelAdapter."""

    def __init__(self, adapter, cache: ResponseCache | None = None):
        self._adapter = adapter
        self._cache = cache or ResponseCache()

    @property
    def model_id(self) -> str:
        return self._adapter.model_id

    @property
    def model_version(self) -> str:
        return self._adapter.model_version

    def generate(self, prompt: str, system_prompt: str | None = None, config: dict | None = None) -> ModelResponse:
        config = config or {}
        full_prompt = f"{system_prompt or ''}|||{prompt}"
        key = ResponseCache.make_key(
            self._adapter.model_id, self._adapter.model_version, full_prompt, config
        )

        cached = self._cache.get(key)
        if cached is not None:
            return cached

        response = self._adapter.generate(prompt, system_prompt, config)
        self._cache.put(key, response, self._adapter.model_version, full_prompt)
        return response

    def batch_generate(self, prompts: list[str], system_prompt: str | None = None, config: dict | None = None) -> list[ModelResponse]:
        return [self.generate(p, system_prompt, config) for p in prompts]

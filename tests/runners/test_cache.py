"""Tests for runners/cache.py — ResponseCache with SQLite backend."""

import pytest

from models.adapters import ModelResponse
from runners.cache import ResponseCache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cache(tmp_path):
    """Create a ResponseCache backed by a temporary SQLite database."""
    c = ResponseCache(cache_dir=tmp_path / "test_cache")
    yield c
    c.close()


def _sample_response(text="KDFW go-around", model_id="claude-sonnet-4-20250514"):
    return ModelResponse(
        text=text,
        model_id=model_id,
        usage={"input_tokens": 50, "output_tokens": 100},
        latency_ms=250.0,
    )


# ---------------------------------------------------------------------------
# Put / Get round-trip
# ---------------------------------------------------------------------------

class TestCacheRoundTrip:
    def test_put_get(self, cache):
        resp = _sample_response()
        key = ResponseCache.make_key("claude-sonnet-4-20250514", "v1", "What happened?")

        cache.put(key, resp, model_version="v1", prompt="What happened?")
        retrieved = cache.get(key)

        assert retrieved is not None
        assert retrieved.text == "KDFW go-around"
        assert retrieved.model_id == "claude-sonnet-4-20250514"
        assert retrieved.usage["input_tokens"] == 50
        assert retrieved.latency_ms == 250.0

    def test_different_prompts_produce_different_keys(self, cache):
        k1 = ResponseCache.make_key("m", "v", "prompt A")
        k2 = ResponseCache.make_key("m", "v", "prompt B")
        assert k1 != k2


# ---------------------------------------------------------------------------
# Cache miss
# ---------------------------------------------------------------------------

class TestCacheMiss:
    def test_get_missing_key_returns_none(self, cache):
        result = cache.get("nonexistent_key_abc123")
        assert result is None


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------

class TestInvalidation:
    def test_invalidate_by_model_version(self, cache):
        r1 = _sample_response(text="response v1")
        r2 = _sample_response(text="response v2")

        k1 = ResponseCache.make_key("m", "v1", "prompt")
        k2 = ResponseCache.make_key("m", "v2", "prompt")

        cache.put(k1, r1, model_version="v1", prompt="prompt")
        cache.put(k2, r2, model_version="v2", prompt="prompt")

        # Invalidate v1 only
        removed = cache.invalidate("v1")
        assert removed == 1

        # v1 gone, v2 still there
        assert cache.get(k1) is None
        assert cache.get(k2) is not None
        assert cache.get(k2).text == "response v2"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestCacheStats:
    def test_stats_hit_miss_counts(self, cache):
        resp = _sample_response()
        key = ResponseCache.make_key("m", "v1", "prompt")
        cache.put(key, resp, model_version="v1", prompt="prompt")

        # 1 hit
        cache.get(key)
        # 2 misses
        cache.get("miss1")
        cache.get("miss2")

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["total_entries"] == 1
        assert stats["hit_rate"] == pytest.approx(1 / 3)

    def test_stats_empty_cache(self, cache):
        stats = cache.stats()
        assert stats["total_entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------

class TestCacheClear:
    def test_clear_removes_all_entries(self, cache):
        for i in range(5):
            r = _sample_response(text=f"resp-{i}")
            k = ResponseCache.make_key("m", "v", f"prompt-{i}")
            cache.put(k, r, model_version="v", prompt=f"prompt-{i}")

        assert cache.stats()["total_entries"] == 5
        cache.clear()
        assert cache.stats()["total_entries"] == 0

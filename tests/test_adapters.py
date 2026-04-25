"""Tests for models/adapters.py — ModelAdapter, AnthropicAdapter, ModelResponse."""

from unittest.mock import patch, MagicMock

import pytest

from models.adapters import ModelAdapter, ModelResponse, AnthropicAdapter, create_adapter


# ---------------------------------------------------------------------------
# ModelResponse dataclass
# ---------------------------------------------------------------------------

class TestModelResponse:
    def test_fields_and_defaults(self):
        resp = ModelResponse(text="hello", model_id="test-model")
        assert resp.text == "hello"
        assert resp.model_id == "test-model"
        assert resp.usage == {}
        assert resp.latency_ms == 0.0
        assert resp.raw_response is None

    def test_all_fields(self):
        resp = ModelResponse(
            text="output",
            model_id="claude-sonnet-4-20250514",
            usage={"input_tokens": 10, "output_tokens": 20},
            latency_ms=150.5,
            raw_response={"id": "msg_123"},
        )
        assert resp.usage["input_tokens"] == 10
        assert resp.latency_ms == 150.5
        assert resp.raw_response == {"id": "msg_123"}


# ---------------------------------------------------------------------------
# ModelAdapter abstract interface
# ---------------------------------------------------------------------------

class TestModelAdapter:
    def test_cannot_instantiate_directly(self):
        """ModelAdapter is abstract; direct instantiation should raise TypeError."""
        with pytest.raises(TypeError):
            ModelAdapter()

    def test_subclass_must_implement_abstract_methods(self):
        """A subclass that doesn't implement all abstract methods cannot be instantiated."""

        class PartialAdapter(ModelAdapter):
            @property
            def model_id(self):
                return "test"

            # model_version and generate are not implemented

        with pytest.raises(TypeError):
            PartialAdapter()


# ---------------------------------------------------------------------------
# AnthropicAdapter construction (mocked)
# ---------------------------------------------------------------------------

class TestAnthropicAdapter:
    @patch("models.adapters.anthropic", create=True)
    def test_construction_with_mock_api_key(self, mock_anthropic_module):
        """AnthropicAdapter should construct without hitting the real API."""
        # Mock the anthropic module at the import site
        mock_anthropic = MagicMock()
        mock_anthropic_module.Anthropic.return_value = MagicMock()
        mock_anthropic_module.AsyncAnthropic.return_value = MagicMock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            adapter = AnthropicAdapter(
                model="claude-sonnet-4-20250514",
                api_key="test-key-12345",
            )
            assert adapter.model_id == "claude-sonnet-4-20250514"
            assert adapter.model_version == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# create_adapter factory
# ---------------------------------------------------------------------------

class TestCreateAdapter:
    @patch("models.adapters.anthropic", create=True)
    def test_create_anthropic(self, mock_anthropic_module):
        """create_adapter('anthropic') should return an AnthropicAdapter."""
        mock_anthropic_module.Anthropic.return_value = MagicMock()
        mock_anthropic_module.AsyncAnthropic.return_value = MagicMock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            adapter = create_adapter("anthropic", api_key="test-key")
            assert isinstance(adapter, AnthropicAdapter)

    def test_create_openai_raises(self):
        """create_adapter('openai') should raise NotImplementedError with guidance."""
        with pytest.raises(NotImplementedError, match="openai.*not supported"):
            create_adapter("openai")

    def test_create_unknown_provider_raises(self):
        with pytest.raises(NotImplementedError, match="not supported"):
            create_adapter("unknown_provider_xyz")

"""
Unit tests for the LlamaIndex callback handler.

These tests do NOT require llama-index to be installed — they exercise the
handler's internal methods directly via the stub base class and mock payloads.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime

from llamaindex.middleware import RagTracerLlamaIndex, _node_to_dict, SimpleRagTracerLlamaIndex
from llamaindex.middleware import CBEventType


# ── _node_to_dict helper ──────────────────────────────────────────────────────

class TestNodeToDict:
    def test_node_with_score_object(self):
        """NodeWithScore-like object (has .score and .node)."""
        inner = MagicMock()
        inner.get_content.return_value = "chunk text"
        inner.metadata = {"source": "doc.pdf", "page_label": "3"}
        inner.node_id = "node-1"

        outer = MagicMock()
        outer.score = 0.92
        outer.node = inner

        result = _node_to_dict(outer)
        assert result["text"] == "chunk text"
        assert result["metadata"]["score"] == pytest.approx(0.92)
        assert result["metadata"]["source"] == "doc.pdf"

    def test_plain_node_with_text_attr(self):
        """Plain node without .node wrapper."""
        node = MagicMock(spec=["text", "metadata"])
        node.text = "plain text"
        node.metadata = {}

        result = _node_to_dict(node)
        assert result["text"] == "plain text"
        assert result["metadata"]["score"] == 0.0

    def test_dict_passthrough(self):
        """Raw dict — treated as plain node, str() used."""
        result = _node_to_dict({"text": "raw", "metadata": {"score": 0.5}})
        # dict has no .score → score 0.0, str(dict) as text
        assert isinstance(result["text"], str)
        assert result["metadata"]["score"] == 0.0


# ── Handler initialisation ────────────────────────────────────────────────────

class TestRagTracerLlamaIndexInit:
    def test_default_session_id_generated(self):
        h = RagTracerLlamaIndex()
        assert h.session_id is not None
        assert len(h.session_id) > 0

    def test_custom_session_id(self):
        h = RagTracerLlamaIndex(session_id="custom-id")
        assert h.session_id == "custom-id"

    def test_query_set_on_init(self):
        h = RagTracerLlamaIndex(query="What is AI?")
        assert h.query == "What is AI?"

    def test_default_auto_save(self):
        h = RagTracerLlamaIndex()
        assert h.auto_save is True

    def test_auto_save_false(self):
        h = RagTracerLlamaIndex(auto_save=False)
        assert h.auto_save is False


# ── on_event_start ────────────────────────────────────────────────────────────

class TestOnEventStart:
    @patch("llamaindex.middleware.get_db")
    def test_query_event_sets_query(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        h = RagTracerLlamaIndex()
        h.on_event_start(
            CBEventType.QUERY,
            payload={CBEventType.QUERY: "What is RAG?"},
        )
        # query is set indirectly via QUERY_STR key; test with correct key
        # (stub CBEventType.QUERY_STR == "query_str")
        h.on_event_start(
            CBEventType.QUERY,
            payload={"query_str": "What is RAG?"},
        )
        assert h.query == "What is RAG?"

    @patch("llamaindex.middleware.get_db")
    def test_retrieve_event_sets_start_time(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        h = RagTracerLlamaIndex(query="q")
        before = time.time()
        h.on_event_start(CBEventType.RETRIEVE, payload={})
        assert h._retrieval_start is not None
        assert h._retrieval_start >= before

    @patch("llamaindex.middleware.get_db")
    def test_llm_event_captures_prompt(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        h = RagTracerLlamaIndex(query="q")
        h.on_event_start(
            CBEventType.LLM,
            payload={"prompt": "Answer this: {q}"},
        )
        assert h._prompt == "Answer this: {q}"


# ── on_event_end ──────────────────────────────────────────────────────────────

class TestOnEventEnd:
    @patch("llamaindex.middleware.get_db")
    def test_retrieve_end_calls_capture_retrieval(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        h = RagTracerLlamaIndex(query="q")
        h._ensure_session()
        h._retrieval_start = time.time()

        mock_capture = MagicMock()
        h._capture = mock_capture

        node = MagicMock()
        node.score = 0.85
        inner = MagicMock()
        inner.get_content.return_value = "doc text"
        inner.metadata = {}
        inner.node_id = "n1"
        node.node = inner

        h.on_event_end(CBEventType.RETRIEVE, payload={"nodes": [node]})
        mock_capture.capture_retrieval.assert_called_once()

    @patch("llamaindex.middleware.get_db")
    def test_llm_end_calls_capture_generation(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        h = RagTracerLlamaIndex(query="q", auto_save=False)
        h._ensure_session()
        h._llm_start = time.time()
        h._prompt = "my prompt"

        mock_capture = MagicMock()
        h._capture = mock_capture

        response = MagicMock()
        response.text = "The answer is RAG."
        response.raw = {}

        h.on_event_end(CBEventType.LLM, payload={"response": response})
        mock_capture.capture_generation.assert_called_once()

    @patch("llamaindex.middleware.get_db")
    def test_llm_end_no_response_skips(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        h = RagTracerLlamaIndex(query="q", auto_save=False)
        h._ensure_session()
        h._llm_start = time.time()

        mock_capture = MagicMock()
        h._capture = mock_capture

        h.on_event_end(CBEventType.LLM, payload={})  # no response key
        mock_capture.capture_generation.assert_not_called()


# ── get_summary ───────────────────────────────────────────────────────────────

class TestGetSummary:
    @patch("llamaindex.middleware.get_db")
    def test_summary_before_session(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        h = RagTracerLlamaIndex(query="What?")
        summary = h.get_summary()
        assert summary["session_id"] == h.session_id
        assert summary["query"] == "What?"

    @patch("llamaindex.middleware.get_db")
    def test_summary_after_session_init(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        h = RagTracerLlamaIndex(query="What?")
        h._ensure_session()
        summary = h.get_summary()
        assert "total_cost" in summary


# ── SimpleRagTracerLlamaIndex context manager ─────────────────────────────────

class TestSimpleRagTracerLlamaIndex:
    @patch("llamaindex.middleware.get_db")
    def test_context_manager_returns_handler(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        with SimpleRagTracerLlamaIndex("test query") as handler:
            assert isinstance(handler, RagTracerLlamaIndex)

    @patch("llamaindex.middleware.get_db")
    def test_context_manager_sets_session_id(self, mock_get_db):
        mock_get_db.return_value = MagicMock()
        tracer = SimpleRagTracerLlamaIndex("query")
        with tracer as _:
            pass
        assert tracer.session_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

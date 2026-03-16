"""
LlamaIndex callback handler for RAGTrace.

Hooks into LlamaIndex's CallbackManager to capture retrieval, embedding,
and LLM events and store them via the RAGTrace core layer.

Usage
-----
from ragtrace.llamaindex import RagTracerLlamaIndex

# Create handler.  It registers itself with the global CallbackManager.
handler = RagTracerLlamaIndex(query="What is RAG?", auto_save=True)

# Run your LlamaIndex query as normal — events are captured automatically.
response = query_engine.query("What is RAG?")

# Inspect results
print(handler.get_summary())
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from core.capture import CaptureSession
from core.cost import count_tokens, calculate_generation_cost
from core.models import RagSession, StoredEvent
from core import get_db

logger = logging.getLogger(__name__)


# ── Sentinel for optional llama_index import ──────────────────────────────────

try:
    from llama_index.core.callbacks import (
        CallbackManager,
        CBEventType,
        EventPayload,
    )
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler

    _LLAMAINDEX_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LLAMAINDEX_AVAILABLE = False

    # Provide a stub so the module can be imported even without llama-index.
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub used when llama-index is not installed."""

        def __init__(self, event_starts_to_ignore=None, event_ends_to_ignore=None):
            pass

    class CBEventType:  # type: ignore[no-redef]
        RETRIEVE = "retrieve"
        LLM = "llm"
        EMBEDDING = "embedding"
        QUERY = "query"

    class EventPayload:  # type: ignore[no-redef]
        QUERY_STR = "query_str"
        NODES = "nodes"
        PROMPT = "prompt"
        COMPLETION = "completion"
        MESSAGES = "messages"
        RESPONSE = "response"
        EMBEDDINGS = "embeddings"
        SERIALIZED = "serialized"


# ── Helper ────────────────────────────────────────────────────────────────────

def _node_to_dict(node: Any) -> Dict[str, Any]:
    """
    Convert a LlamaIndex NodeWithScore (or plain Node) to a plain dict
    compatible with RetrievedChunk / StoredEvent data shapes.
    """
    score: float = 0.0
    if hasattr(node, "score") and node.score is not None:
        score = float(node.score)

    # Unwrap NodeWithScore → Node if necessary
    raw_node = getattr(node, "node", node)

    text: str = ""
    if hasattr(raw_node, "get_content"):
        text = raw_node.get_content()
    elif hasattr(raw_node, "text"):
        text = raw_node.text
    else:
        text = str(raw_node)

    metadata: Dict[str, Any] = {}
    if hasattr(raw_node, "metadata"):
        metadata = raw_node.metadata or {}

    return {
        "text": text,
        "metadata": {
            "source": metadata.get("file_name") or metadata.get("source"),
            "page": metadata.get("page_label") or metadata.get("page"),
            "score": score,
            "document_id": metadata.get("doc_id") or getattr(raw_node, "node_id", None),
        },
    }


# ── Main handler ──────────────────────────────────────────────────────────────

class RagTracerLlamaIndex(BaseCallbackHandler):
    """
    LlamaIndex CallbackHandler that captures RAG events into RAGTrace.

    Captures:
    - RETRIEVE events → RetrievalEvent
    - LLM events      → PromptEvent + GenerationEvent
    - QUERY events    → extracts the user query

    Parameters
    ----------
    session_id : str, optional
        Reuse an existing session.  Creates a new one if not provided.
    query : str, optional
        Override the query string (auto-detected from QUERY event otherwise).
    api_url : str, optional
        Unused for now; reserved for future remote-reporting mode.
    auto_save : bool
        If True, flush events to DB after each LLM completion.
    model : str
        Default model name used for cost estimation when not available
        in the LLM response payload.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        query: Optional[str] = None,
        api_url: Optional[str] = None,
        auto_save: bool = True,
        model: str = "gpt-3.5-turbo",
    ):
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[],
        )

        self.session_id: str = session_id or str(uuid.uuid4())
        self.query: Optional[str] = query
        self.auto_save: bool = auto_save
        self._default_model: str = model

        # Timing
        self._retrieval_start: Optional[float] = None
        self._llm_start: Optional[float] = None

        # Captured data (raw, before building events)
        self._nodes: List[Any] = []
        self._prompt: Optional[str] = None
        self._response: Optional[str] = None

        # Session / capture state
        self._session: Optional[RagSession] = None
        self._capture: Optional[CaptureSession] = None

    # ── Session init ──────────────────────────────────────────────────────────

    def _ensure_session(self) -> None:
        if self._session is not None:
            return

        query = self.query or "unknown query"
        self._session = RagSession(id=self.session_id, query=query)

        try:
            db = get_db()
            db.create_session(self._session)
        except Exception as exc:
            logger.warning("RAGTrace: could not create session in DB: %s", exc)

        self._capture = CaptureSession(session_id=self.session_id, query=query)

    # ── CallbackHandler API ───────────────────────────────────────────────────

    def on_event_start(
        self,
        event_type: Any,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        payload = payload or {}

        event_name = event_type.value if hasattr(event_type, "value") else str(event_type)

        if event_name == CBEventType.QUERY:
            query_str = payload.get(EventPayload.QUERY_STR, "")
            if query_str and not self.query:
                self.query = query_str
            self._ensure_session()

        elif event_name == CBEventType.RETRIEVE:
            self._retrieval_start = time.time()
            self._ensure_session()

        elif event_name in (CBEventType.LLM,):
            self._llm_start = time.time()
            self._ensure_session()

            # Capture prompt from messages or plain prompt key
            messages = payload.get(EventPayload.MESSAGES)
            if messages:
                # OpenAI-style chat messages list
                self._prompt = "\n".join(
                    f"{m.role}: {m.content}"
                    for m in messages
                    if hasattr(m, "content")
                )
            else:
                self._prompt = payload.get(EventPayload.PROMPT, "")

        return event_id or str(uuid.uuid4())

    def on_event_end(
        self,
        event_type: Any,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        payload = payload or {}

        event_name = event_type.value if hasattr(event_type, "value") else str(event_type)

        if event_name == CBEventType.RETRIEVE:
            self._handle_retrieve_end(payload)

        elif event_name == CBEventType.LLM:
            self._handle_llm_end(payload)

    def on_event_error(self, error: Exception, **kwargs: Any) -> None:
        logger.error("RAGTrace LlamaIndex handler error: %s", error)

    # ── Internal event handlers ───────────────────────────────────────────────

    def _handle_retrieve_end(self, payload: Dict[str, Any]) -> None:
        if self._capture is None:
            return

        duration_ms = int((time.time() - (self._retrieval_start or time.time())) * 1000)

        nodes = payload.get(EventPayload.NODES, [])
        doc_dicts = [_node_to_dict(n) for n in nodes]
        self._nodes = doc_dicts

        try:
            self._capture.capture_retrieval(
                documents=doc_dicts,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.error("RAGTrace: retrieval capture failed: %s", exc)

    def _handle_llm_end(self, payload: Dict[str, Any]) -> None:
        if self._capture is None:
            return

        duration_ms = int((time.time() - (self._llm_start or time.time())) * 1000)

        # Extract response text
        response_obj = payload.get(EventPayload.RESPONSE) or payload.get(
            EventPayload.COMPLETION
        )
        if response_obj is None:
            return

        if hasattr(response_obj, "text"):
            response_text = response_obj.text
        elif hasattr(response_obj, "message"):
            response_text = getattr(response_obj.message, "content", str(response_obj))
        else:
            response_text = str(response_obj)

        # Token counts
        serialized = payload.get(EventPayload.SERIALIZED, {}) or {}
        model = (
            serialized.get("model")
            or serialized.get("model_name")
            or self._default_model
        )

        # Try to get usage from raw response
        raw_response = getattr(response_obj, "raw", None) or {}
        usage = raw_response.get("usage", {}) if isinstance(raw_response, dict) else {}
        input_tokens = usage.get("prompt_tokens") or count_tokens(
            self._prompt or "", model
        )
        output_tokens = usage.get("completion_tokens") or count_tokens(
            response_text, model
        )

        # Capture prompt event
        if self._prompt:
            try:
                self._capture.capture_prompt(
                    prompt=self._prompt,
                    model=model,
                )
            except Exception as exc:
                logger.error("RAGTrace: prompt capture failed: %s", exc)

        # Capture generation event
        try:
            self._capture.capture_generation(
                response=response_text,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.error("RAGTrace: generation capture failed: %s", exc)

        if self.auto_save:
            self.save()

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        """Flush captured events to the database."""
        if self._capture is None or self._session is None:
            return

        try:
            db = get_db()
            session = self._capture.to_session()
            db.update_session(
                self.session_id,
                completed_at=session.completed_at,
                total_cost=session.total_cost,
                total_duration_ms=session.total_duration_ms,
                model=session.model,
            )
            for event in self._capture.to_stored_events():
                db.store_event(event)
        except Exception as exc:
            logger.error("RAGTrace: failed to save session: %s", exc)

    # ── Utility ───────────────────────────────────────────────────────────────

    def get_session_id(self) -> str:
        return self.session_id

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary dict of the captured session."""
        if self._capture is None:
            return {"session_id": self.session_id, "query": self.query}

        return {
            "session_id": self.session_id,
            "query": self.query,
            "has_retrieval": self._capture.retrieval_event is not None,
            "has_prompt": self._capture.prompt_event is not None,
            "has_generation": self._capture.generation_event is not None,
            "total_cost": self._capture.get_total_cost(),
            "total_duration_ms": self._capture.get_total_duration(),
        }


# ── Context-manager convenience ───────────────────────────────────────────────

class SimpleRagTracerLlamaIndex:
    """
    Context-manager wrapper for RagTracerLlamaIndex.

    Usage::

        with SimpleRagTracerLlamaIndex("What is climate change?") as tracer:
            response = query_engine.query("What is climate change?")

        print("Cost:", tracer.cost)
        print("Session:", tracer.session_id)
    """

    def __init__(self, query: str, model: str = "gpt-3.5-turbo"):
        self.handler = RagTracerLlamaIndex(query=query, auto_save=True, model=model)
        self.session_id: Optional[str] = None
        self.cost: float = 0.0

    def __enter__(self) -> RagTracerLlamaIndex:
        return self.handler

    def __exit__(self, *args: Any) -> None:
        self.handler.save()
        self.session_id = self.handler.get_session_id()
        if self.handler._capture:
            self.cost = self.handler._capture.get_total_cost()

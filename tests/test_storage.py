"""
Unit tests for the storage module.

Tests database CRUD operations for sessions, events, and snapshots
using the actual model schema (Pydantic v2 field names).
"""

import pytest
import tempfile
import os
from datetime import datetime

from core.storage import Database
from core.models import (
    RagSession,
    RetrievedChunk,
    ChunkMetadata,
    RetrievalEvent,
    PromptEvent,
    GenerationEvent,
    Snapshot,
    StoredEvent,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_db():
    """Temporary SQLite database, removed after each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    yield db
    if db.conn:
        db.conn.close()
    os.unlink(path)


@pytest.fixture
def sample_session():
    return RagSession(query="What is RAG?")


@pytest.fixture
def sample_retrieval_event(sample_session):
    return RetrievalEvent(
        session_id=sample_session.id,
        chunks=[
            RetrievedChunk(
                text="RAG stands for Retrieval-Augmented Generation",
                metadata=ChunkMetadata(source="doc1.txt", page=1, score=0.95),
            )
        ],
        duration_ms=150,
        embedding_tokens=12,
        embedding_cost=0.0001,
        retrieval_method="vector_search",
    )


@pytest.fixture
def sample_prompt_event(sample_session):
    return PromptEvent(
        session_id=sample_session.id,
        prompt="Context: RAG info\n\nQuestion: What is RAG?",
        token_count=25,
        template_name="qa_template",
    )


@pytest.fixture
def sample_generation_event(sample_session):
    return GenerationEvent(
        session_id=sample_session.id,
        response="RAG is Retrieval-Augmented Generation.",
        model="gpt-3.5-turbo",
        input_tokens=25,
        output_tokens=10,
        cost=0.0036,
        duration_ms=1200,
        temperature=0.7,
    )


@pytest.fixture
def sample_stored_retrieval(sample_session, sample_retrieval_event):
    return StoredEvent(
        session_id=sample_session.id,
        event_type="retrieval",
        data=sample_retrieval_event.model_dump(mode="json"),
    )


@pytest.fixture
def sample_stored_prompt(sample_session, sample_prompt_event):
    return StoredEvent(
        session_id=sample_session.id,
        event_type="prompt",
        data=sample_prompt_event.model_dump(mode="json"),
    )


@pytest.fixture
def sample_stored_generation(sample_session, sample_generation_event):
    return StoredEvent(
        session_id=sample_session.id,
        event_type="generation",
        data=sample_generation_event.model_dump(mode="json"),
    )


# ── Schema ────────────────────────────────────────────────────────────────────

class TestDatabaseInitialization:
    def test_database_creation(self, temp_db):
        assert temp_db.conn is not None
        assert temp_db.db_path.exists()

    def test_schema_tables_created(self, temp_db):
        cursor = temp_db.conn.cursor()
        for table in ("sessions", "events", "snapshots"):
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            assert cursor.fetchone() is not None, f"Table '{table}' not found"

    def test_indexes_created(self, temp_db):
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        assert any("session" in idx.lower() for idx in indexes)


# ── Session CRUD ──────────────────────────────────────────────────────────────

class TestSessionOperations:
    def test_create_and_get_session(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        retrieved = temp_db.get_session(sample_session.id)
        assert retrieved is not None
        assert retrieved.id == sample_session.id
        assert retrieved.query == sample_session.query

    def test_get_nonexistent_session_returns_none(self, temp_db):
        assert temp_db.get_session("nonexistent-id") is None

    def test_list_sessions_empty(self, temp_db):
        assert temp_db.list_sessions() == []

    def test_list_sessions_returns_all(self, temp_db):
        for i in range(5):
            temp_db.create_session(RagSession(query=f"Query {i}"))
        assert len(temp_db.list_sessions(limit=10)) == 5

    def test_list_sessions_respects_limit(self, temp_db):
        for i in range(10):
            temp_db.create_session(RagSession(query=f"Query {i}"))
        assert len(temp_db.list_sessions(limit=3)) == 3

    def test_update_session_total_cost(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        temp_db.update_session(sample_session.id, total_cost=0.042)
        retrieved = temp_db.get_session(sample_session.id)
        assert retrieved.total_cost == pytest.approx(0.042)

    def test_update_session_model(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        temp_db.update_session(sample_session.id, model="gpt-4")
        retrieved = temp_db.get_session(sample_session.id)
        assert retrieved.model == "gpt-4"

    def test_delete_session(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        deleted = temp_db.delete_session(sample_session.id)
        assert deleted is True
        assert temp_db.get_session(sample_session.id) is None

    def test_delete_nonexistent_returns_false(self, temp_db):
        assert temp_db.delete_session("does-not-exist") is False

    def test_get_latest_session(self, temp_db):
        for i in range(3):
            temp_db.create_session(RagSession(query=f"Query {i}"))
        latest = temp_db.get_latest_session()
        assert latest is not None
        assert latest.query == "Query 2"


# ── Event CRUD ────────────────────────────────────────────────────────────────

class TestEventOperations:
    def test_store_and_get_retrieval_event(
        self, temp_db, sample_session, sample_stored_retrieval
    ):
        temp_db.create_session(sample_session)
        stored = temp_db.store_event(sample_stored_retrieval)
        assert stored.id is not None
        events = temp_db.get_events(sample_session.id)
        assert events["retrieval"] is not None

    def test_store_prompt_event(self, temp_db, sample_session, sample_stored_prompt):
        temp_db.create_session(sample_session)
        temp_db.store_event(sample_stored_prompt)
        events = temp_db.get_events(sample_session.id)
        assert events["prompt"] is not None

    def test_store_generation_event(
        self, temp_db, sample_session, sample_stored_generation
    ):
        temp_db.create_session(sample_session)
        temp_db.store_event(sample_stored_generation)
        events = temp_db.get_events(sample_session.id)
        assert events["generation"] is not None

    def test_store_all_three_events(
        self, temp_db, sample_session,
        sample_stored_retrieval, sample_stored_prompt, sample_stored_generation
    ):
        temp_db.create_session(sample_session)
        for event in (sample_stored_retrieval, sample_stored_prompt, sample_stored_generation):
            temp_db.store_event(event)
        events = temp_db.get_events(sample_session.id)
        assert events["retrieval"] is not None
        assert events["prompt"] is not None
        assert events["generation"] is not None

    def test_get_events_empty_session(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        events = temp_db.get_events(sample_session.id)
        assert events["retrieval"] is None
        assert events["prompt"] is None
        assert events["generation"] is None

    def test_get_events_nonexistent_session(self, temp_db):
        events = temp_db.get_events("nonexistent")
        assert events["retrieval"] is None


# ── Session Detail & Cost ─────────────────────────────────────────────────────

class TestSessionDetail:
    def test_get_session_detail(
        self, temp_db, sample_session,
        sample_stored_retrieval, sample_stored_prompt, sample_stored_generation
    ):
        temp_db.create_session(sample_session)
        for event in (sample_stored_retrieval, sample_stored_prompt, sample_stored_generation):
            temp_db.store_event(event)

        detail = temp_db.get_session_detail(sample_session.id)
        assert detail is not None
        assert detail.session.id == sample_session.id
        assert detail.retrieval is not None
        assert detail.prompt is not None
        assert detail.generation is not None

    def test_get_session_detail_not_found(self, temp_db):
        assert temp_db.get_session_detail("no-such-id") is None

    def test_get_cost_breakdown(
        self, temp_db, sample_session,
        sample_stored_retrieval, sample_stored_generation
    ):
        temp_db.create_session(sample_session)
        temp_db.store_event(sample_stored_retrieval)
        temp_db.store_event(sample_stored_generation)
        cost = temp_db.get_cost_breakdown(sample_session.id)
        assert cost is not None
        assert cost.total_cost > 0

    def test_get_cost_breakdown_no_events(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        cost = temp_db.get_cost_breakdown(sample_session.id)
        assert cost.total_cost == pytest.approx(0.0)


# ── Snapshot CRUD ─────────────────────────────────────────────────────────────

class TestSnapshotOperations:
    def _make_snap(self, session_id: str, query: str = "What is RAG?") -> Snapshot:
        return Snapshot(
            session_id=session_id,
            query=query,
            chunks=[{"text": "chunk text", "metadata": {"score": 0.9}}],
            answer="RAG is Retrieval-Augmented Generation.",
            cost=0.005,
            tags=["v1", "test"],
            model="gpt-3.5-turbo",
        )

    def test_create_and_get_snapshot(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        snap = self._make_snap(sample_session.id)
        created = temp_db.create_snapshot(snap)
        retrieved = temp_db.get_snapshot(created.id)
        assert retrieved is not None
        assert retrieved.query == snap.query
        assert retrieved.tags == ["v1", "test"]

    def test_get_nonexistent_snapshot(self, temp_db):
        assert temp_db.get_snapshot("no-such-snap") is None

    def test_list_snapshots(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        for i in range(3):
            temp_db.create_snapshot(self._make_snap(sample_session.id, f"Query {i}"))
        assert len(temp_db.list_snapshots(limit=10)) == 3

    def test_list_snapshots_respects_limit(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        for i in range(5):
            temp_db.create_snapshot(self._make_snap(sample_session.id, f"Query {i}"))
        assert len(temp_db.list_snapshots(limit=2)) == 2

    def test_delete_snapshot(self, temp_db, sample_session):
        temp_db.create_session(sample_session)
        snap = temp_db.create_snapshot(self._make_snap(sample_session.id))
        deleted = temp_db.delete_snapshot(snap.id)
        assert deleted is True
        assert temp_db.get_snapshot(snap.id) is None

    def test_delete_nonexistent_snapshot(self, temp_db):
        assert temp_db.delete_snapshot("no-such-id") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

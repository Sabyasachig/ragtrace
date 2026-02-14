"""
Unit tests for storage module.

Tests database operations including sessions, events, and snapshots.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from core.storage import Database
from core.models import (
    RagSession,
    RetrievalEvent,
    PromptEvent,
    GenerationEvent,
    Snapshot,
    RetrievedChunk,
    ChunkMetadata,
    CostBreakdown,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Create database (auto-connects and initializes)
    db = Database(path)
    
    yield db
    
    # Cleanup
    if db.conn:
        db.conn.close()
    os.unlink(path)


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return RagSession(
        session_id="test-session-1",
        query="What is RAG?",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_retrieval_event():
    """Create a sample retrieval event."""
    return RetrievalEvent(
        session_id="test-session-1",
        timestamp=datetime.utcnow(),
        chunks=[
            RetrievedChunk(
                content="RAG stands for Retrieval-Augmented Generation",
                metadata=ChunkMetadata(
                    source="doc1.txt",
                    page=1,
                    score=0.95,
                ),
            )
        ],
        duration_ms=150.0,
        retriever_name="FAISS",
        top_k=5,
    )


@pytest.fixture
def sample_prompt_event():
    """Create a sample prompt event."""
    return PromptEvent(
        session_id="test-session-1",
        timestamp=datetime.utcnow(),
        prompt_template="Context: {context}\n\nQuestion: {question}",
        filled_prompt="Context: RAG info\n\nQuestion: What is RAG?",
        template_vars={"context": "RAG info", "question": "What is RAG?"},
    )


@pytest.fixture
def sample_generation_event():
    """Create a sample generation event."""
    return GenerationEvent(
        session_id="test-session-1",
        timestamp=datetime.utcnow(),
        model="gpt-3.5-turbo",
        prompt="What is RAG?",
        response="RAG is Retrieval-Augmented Generation",
        cost_breakdown=CostBreakdown(
            embedding_cost=0.0001,
            input_cost=0.0015,
            output_cost=0.002,
            total_cost=0.0036,
        ),
        duration_ms=1200.0,
        tokens_input=10,
        tokens_output=15,
    )


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""
    
    def test_database_creation(self, temp_db):
        """Test that database is created successfully."""
        assert temp_db.conn is not None
        assert temp_db.db_path.exists()
    
    def test_schema_initialization(self, temp_db):
        """Test that schema tables are created."""
        cursor = temp_db.conn.cursor()
        
        # Check sessions table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert cursor.fetchone() is not None
        
        # Check events table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        )
        assert cursor.fetchone() is not None
        
        # Check snapshots table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='snapshots'"
        )
        assert cursor.fetchone() is not None
    
    def test_indexes_created(self, temp_db):
        """Test that indexes are created."""
        cursor = temp_db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        
        # Should have indexes on session_id and timestamp
        assert any("session" in idx.lower() for idx in indexes)


class TestSessionOperations:
    """Test CRUD operations for sessions."""
    
    def test_create_session(self, temp_db, sample_session):
        """Test creating a new session."""
        temp_db.create_session(sample_session)
        
        # Retrieve and verify
        retrieved = temp_db.get_session(sample_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == sample_session.session_id
        assert retrieved.query == sample_session.query
    
    def test_get_nonexistent_session(self, temp_db):
        """Test retrieving a session that doesn't exist."""
        result = temp_db.get_session("nonexistent-id")
        assert result is None
    
    def test_list_sessions_empty(self, temp_db):
        """Test listing sessions when database is empty."""
        sessions = temp_db.list_sessions()
        assert len(sessions) == 0
    
    def test_list_sessions(self, temp_db):
        """Test listing multiple sessions."""
        # Create multiple sessions
        for i in range(5):
            session = RagSession(
                session_id=f"test-session-{i}",
                query=f"Query {i}",
                created_at=datetime.utcnow(),
            )
            temp_db.create_session(session)
        
        # List sessions
        sessions = temp_db.list_sessions(limit=10)
        assert len(sessions) == 5
    
    def test_list_sessions_with_limit(self, temp_db):
        """Test listing sessions with limit."""
        # Create multiple sessions
        for i in range(10):
            session = RagSession(
                session_id=f"test-session-{i}",
                query=f"Query {i}",
                created_at=datetime.utcnow(),
            )
            temp_db.create_session(session)
        
        # List with limit
        sessions = temp_db.list_sessions(limit=5)
        assert len(sessions) == 5
    
    def test_update_session(self, temp_db, sample_session):
        """Test updating session metadata."""
        # Create session
        temp_db.create_session(sample_session)
        
        # Update metadata
        new_metadata = {"status": "completed", "duration": 2.5}
        temp_db.update_session(sample_session.session_id, metadata=new_metadata)
        
        # Verify update
        retrieved = temp_db.get_session(sample_session.session_id)
        assert retrieved.metadata == new_metadata
    
    def test_delete_session(self, temp_db, sample_session):
        """Test deleting a session."""
        # Create session
        temp_db.create_session(sample_session)
        
        # Delete
        temp_db.delete_session(sample_session.session_id)
        
        # Verify deletion
        retrieved = temp_db.get_session(sample_session.session_id)
        assert retrieved is None


class TestEventOperations:
    """Test CRUD operations for events."""
    
    def test_add_retrieval_event(self, temp_db, sample_session, sample_retrieval_event):
        """Test adding a retrieval event."""
        temp_db.create_session(sample_session)
        temp_db.add_event(sample_retrieval_event)
        
        # Retrieve events
        events = temp_db.get_session_events(sample_session.session_id)
        assert len(events) == 1
        assert events[0].event_type == "retrieval"
    
    def test_add_prompt_event(self, temp_db, sample_session, sample_prompt_event):
        """Test adding a prompt event."""
        temp_db.create_session(sample_session)
        temp_db.add_event(sample_prompt_event)
        
        # Retrieve events
        events = temp_db.get_session_events(sample_session.session_id)
        assert len(events) == 1
        assert events[0].event_type == "prompt"
    
    def test_add_generation_event(self, temp_db, sample_session, sample_generation_event):
        """Test adding a generation event."""
        temp_db.create_session(sample_session)
        temp_db.add_event(sample_generation_event)
        
        # Retrieve events
        events = temp_db.get_session_events(sample_session.session_id)
        assert len(events) == 1
        assert events[0].event_type == "generation"
    
    def test_add_multiple_events(self, temp_db, sample_session, 
                                 sample_retrieval_event, sample_prompt_event, 
                                 sample_generation_event):
        """Test adding multiple events."""
        temp_db.create_session(sample_session)
        temp_db.add_event(sample_retrieval_event)
        temp_db.add_event(sample_prompt_event)
        temp_db.add_event(sample_generation_event)
        
        # Retrieve events
        events = temp_db.get_session_events(sample_session.session_id)
        assert len(events) == 3
    
    def test_get_events_empty_session(self, temp_db, sample_session):
        """Test getting events for session with no events."""
        temp_db.create_session(sample_session)
        events = temp_db.get_session_events(sample_session.session_id)
        assert len(events) == 0
    
    def test_get_events_nonexistent_session(self, temp_db):
        """Test getting events for nonexistent session."""
        events = temp_db.get_session_events("nonexistent-id")
        assert len(events) == 0


class TestSnapshotOperations:
    """Test CRUD operations for snapshots."""
    
    def test_create_snapshot(self, temp_db, sample_session):
        """Test creating a snapshot."""
        temp_db.create_session(sample_session)
        
        # Create snapshot
        snapshot = Snapshot(
            snapshot_id="snap-1",
            session_id=sample_session.session_id,
            name="Test Snapshot",
            description="A test snapshot",
            created_at=datetime.utcnow(),
        )
        temp_db.create_snapshot(snapshot)
        
        # Verify
        retrieved = temp_db.get_snapshot("snap-1")
        assert retrieved is not None
        assert retrieved.name == "Test Snapshot"
    
    def test_list_snapshots(self, temp_db, sample_session):
        """Test listing snapshots."""
        temp_db.create_session(sample_session)
        
        # Create multiple snapshots
        for i in range(3):
            snapshot = Snapshot(
                snapshot_id=f"snap-{i}",
                session_id=sample_session.session_id,
                name=f"Snapshot {i}",
                created_at=datetime.utcnow(),
            )
            temp_db.create_snapshot(snapshot)
        
        # List snapshots
        snapshots = temp_db.list_snapshots()
        assert len(snapshots) == 3
    
    def test_delete_snapshot(self, temp_db, sample_session):
        """Test deleting a snapshot."""
        temp_db.create_session(sample_session)
        
        # Create snapshot
        snapshot = Snapshot(
            snapshot_id="snap-1",
            session_id=sample_session.session_id,
            name="Test Snapshot",
            created_at=datetime.utcnow(),
        )
        temp_db.create_snapshot(snapshot)
        
        # Delete
        temp_db.delete_snapshot("snap-1")
        
        # Verify deletion
        retrieved = temp_db.get_snapshot("snap-1")
        assert retrieved is None


class TestCostCalculations:
    """Test cost calculation aggregations."""
    
    def test_get_session_costs(self, temp_db, sample_session, sample_generation_event):
        """Test getting total costs for a session."""
        temp_db.create_session(sample_session)
        temp_db.add_event(sample_generation_event)
        
        # Get costs
        costs = temp_db.get_session_costs(sample_session.session_id)
        assert costs is not None
        assert costs.total_cost > 0
    
    def test_get_session_costs_no_events(self, temp_db, sample_session):
        """Test getting costs for session with no events."""
        temp_db.create_session(sample_session)
        costs = temp_db.get_session_costs(sample_session.session_id)
        assert costs.total_cost == 0


class TestDatabaseCleanup:
    """Test database cleanup operations."""
    
    def test_clear_all_sessions(self, temp_db, sample_session):
        """Test clearing all sessions."""
        # Create some sessions
        for i in range(5):
            session = RagSession(
                session_id=f"test-session-{i}",
                query=f"Query {i}",
                created_at=datetime.utcnow(),
            )
            temp_db.create_session(session)
        
        # Clear all
        temp_db.clear_all()
        
        # Verify empty
        sessions = temp_db.list_sessions()
        assert len(sessions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

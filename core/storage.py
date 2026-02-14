"""
SQLite storage layer for RAG Debugger.

This module handles all database operations including:
- Session management
- Event storage and retrieval
- Snapshot management
- Cost tracking

We use SQLite for simplicity and portability in the MVP.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from .models import (
    RagSession,
    RetrievalEvent,
    PromptEvent,
    GenerationEvent,
    Snapshot,
    SessionDetail,
    CostBreakdown,
    StoredEvent,
)

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for RAG Debugger.
    
    Handles connection management, schema creation, and all CRUD operations.
    Uses JSON for storing complex objects in a simple schema.
    """
    
    def __init__(self, db_path: str = "~/.ragdebug/ragdebug.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema if it doesn't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        
        cursor = self.conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                completed_at DATETIME,
                total_cost REAL,
                total_duration_ms INTEGER,
                model TEXT
            )
        """)
        
        # Events table (polymorphic)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                query TEXT NOT NULL,
                chunks TEXT NOT NULL,
                answer TEXT NOT NULL,
                cost REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                tags TEXT,
                model TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session 
            ON events(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_created 
            ON sessions(created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_tags 
            ON snapshots(tags)
        """)
        
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    # Session operations
    
    def create_session(self, session: RagSession) -> RagSession:
        """
        Create a new RAG session.
        
        Args:
            session: RagSession object to store
            
        Returns:
            The created session
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (id, query, created_at, completed_at, total_cost, total_duration_ms, model)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            session.query,
            session.created_at.isoformat(),
            session.completed_at.isoformat() if session.completed_at else None,
            session.total_cost,
            session.total_duration_ms,
            session.model
        ))
        self.conn.commit()
        logger.info(f"Created session {session.id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[RagSession]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            RagSession if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return RagSession(
            id=row["id"],
            query=row["query"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            total_cost=row["total_cost"],
            total_duration_ms=row["total_duration_ms"],
            model=row["model"]
        )
    
    def list_sessions(self, limit: int = 10, offset: int = 0) -> List[RagSession]:
        """
        List recent sessions.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Offset for pagination
            
        Returns:
            List of sessions, most recent first
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append(RagSession(
                id=row["id"],
                query=row["query"],
                created_at=datetime.fromisoformat(row["created_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                total_cost=row["total_cost"],
                total_duration_ms=row["total_duration_ms"],
                model=row["model"]
            ))
        
        return sessions
    
    def update_session(self, session_id: str, **updates) -> bool:
        """
        Update session fields.
        
        Args:
            session_id: Session ID to update
            **updates: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        # Build dynamic UPDATE query based on provided fields
        valid_fields = ["completed_at", "total_cost", "total_duration_ms", "model"]
        update_fields = []
        values = []
        
        for field, value in updates.items():
            if field in valid_fields:
                update_fields.append(f"{field} = ?")
                if field == "completed_at" and isinstance(value, datetime):
                    values.append(value.isoformat())
                else:
                    values.append(value)
        
        if not update_fields:
            return False
        
        values.append(session_id)
        query = f"UPDATE sessions SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor = self.conn.cursor()
        cursor.execute(query, values)
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its events.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    # Event operations
    
    def store_event(self, event: StoredEvent) -> StoredEvent:
        """
        Store an event.
        
        Args:
            event: StoredEvent to store
            
        Returns:
            The stored event
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO events (id, session_id, event_type, timestamp, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.id,
            event.session_id,
            event.event_type,
            event.timestamp.isoformat(),
            json.dumps(event.data)
        ))
        self.conn.commit()
        logger.debug(f"Stored {event.event_type} event for session {event.session_id}")
        return event
    
    def get_events(self, session_id: str) -> Dict[str, Any]:
        """
        Get all events for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dictionary with retrieval, prompt, and generation events
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM events 
            WHERE session_id = ? 
            ORDER BY timestamp ASC
        """, (session_id,))
        
        events = {
            "retrieval": None,
            "prompt": None,
            "generation": None
        }
        
        for row in cursor.fetchall():
            event_type = row["event_type"]
            data = json.loads(row["data"])
            
            if event_type == "retrieval":
                events["retrieval"] = RetrievalEvent(**data)
            elif event_type == "prompt":
                events["prompt"] = PromptEvent(**data)
            elif event_type == "generation":
                events["generation"] = GenerationEvent(**data)
        
        return events
    
    def get_session_detail(self, session_id: str) -> Optional[SessionDetail]:
        """
        Get complete session details including all events.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionDetail if session exists, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        events = self.get_events(session_id)
        cost_breakdown = self.get_cost_breakdown(session_id)
        
        return SessionDetail(
            session=session,
            retrieval=events["retrieval"],
            prompt=events["prompt"],
            generation=events["generation"],
            cost_breakdown=cost_breakdown
        )
    
    def get_cost_breakdown(self, session_id: str) -> Optional[CostBreakdown]:
        """
        Calculate cost breakdown for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            CostBreakdown if costs available, None otherwise
        """
        events = self.get_events(session_id)
        
        embedding_cost = 0.0
        input_cost = 0.0
        output_cost = 0.0
        
        if events["retrieval"]:
            embedding_cost = events["retrieval"].embedding_cost
        
        if events["generation"]:
            # We'll calculate this properly in cost.py
            # For now, use the stored cost
            total_gen_cost = events["generation"].cost
            # Estimate split (this is rough, will be refined in cost.py)
            if events["generation"].input_tokens and events["generation"].output_tokens:
                total_tokens = events["generation"].input_tokens + events["generation"].output_tokens
                input_cost = total_gen_cost * (events["generation"].input_tokens / total_tokens)
                output_cost = total_gen_cost * (events["generation"].output_tokens / total_tokens)
            else:
                input_cost = total_gen_cost / 2
                output_cost = total_gen_cost / 2
        
        total_cost = embedding_cost + input_cost + output_cost
        
        return CostBreakdown(
            session_id=session_id,
            embedding_cost=embedding_cost,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost
        )
    
    # Snapshot operations
    
    def create_snapshot(self, snapshot: Snapshot) -> Snapshot:
        """
        Create a snapshot for regression testing.
        
        Args:
            snapshot: Snapshot to store
            
        Returns:
            The created snapshot
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO snapshots (id, session_id, query, chunks, answer, cost, timestamp, tags, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.id,
            snapshot.session_id,
            snapshot.query,
            json.dumps(snapshot.chunks),
            snapshot.answer,
            snapshot.cost,
            snapshot.timestamp.isoformat(),
            json.dumps(snapshot.tags),
            snapshot.model
        ))
        self.conn.commit()
        logger.info(f"Created snapshot {snapshot.id}")
        return snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """
        Retrieve a snapshot by ID.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return Snapshot(
            id=row["id"],
            session_id=row["session_id"],
            query=row["query"],
            chunks=json.loads(row["chunks"]),
            answer=row["answer"],
            cost=row["cost"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            model=row["model"]
        )
    
    def list_snapshots(self, limit: int = 10) -> List[Snapshot]:
        """
        List recent snapshots.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of snapshots, most recent first
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM snapshots 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append(Snapshot(
                id=row["id"],
                session_id=row["session_id"],
                query=row["query"],
                chunks=json.loads(row["chunks"]),
                answer=row["answer"],
                cost=row["cost"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                tags=json.loads(row["tags"]) if row["tags"] else [],
                model=row["model"]
            ))
        
        return snapshots
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot.
        
        Args:
            snapshot_id: Snapshot ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    def get_latest_session(self) -> Optional[RagSession]:
        """
        Get the most recent session.
        
        Returns:
            Most recent session, or None if no sessions exist
        """
        sessions = self.list_sessions(limit=1)
        return sessions[0] if sessions else None


# Global database instance (singleton pattern for MVP)
_db_instance: Optional[Database] = None


def get_db(db_path: str = "~/.ragdebug/ragdebug.db") -> Database:
    """
    Get or create global database instance.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance


def close_db():
    """Close global database instance."""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None

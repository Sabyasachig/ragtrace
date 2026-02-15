#!/usr/bin/env python3
"""Quick test to add sample data directly to database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import get_db
from core.models import RagSession, EventType
from datetime import datetime
import uuid
import json

def add_test_data():
    db = get_db()
    print("Adding test data directly...")
    
    # Add a simple session
    session_id = str(uuid.uuid4())
    
    # Use raw SQL to insert
    db.conn.execute("""
        INSERT INTO sessions (id, query, created_at, completed_at, total_cost, total_duration_ms, model)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        "Test query: What is machine learning?",
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat(),
        0.0123,
        3500,
        "gpt-4"
    ))
    
    # Add an event
    event_id = str(uuid.uuid4())
    db.conn.execute("""
        INSERT INTO events (id, session_id, event_type, timestamp, data)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event_id,
        session_id,
        "llm_end",
        datetime.utcnow().isoformat(),
        json.dumps({"model": "gpt-4", "tokens": 150, "cost": 0.0123})
    ))
    
    db.conn.commit()
    
    print(f"✅ Added session: {session_id[:8]}...")
    print(f"✅ Added event: {event_id[:8]}...")
    
    # Verify
    cursor = db.conn.execute("SELECT COUNT(*) FROM sessions")
    count = cursor.fetchone()[0]
    print(f"✅ Total sessions in DB: {count}")

if __name__ == "__main__":
    add_test_data()

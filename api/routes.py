"""
API routes for RAG Debugger.

Defines all API endpoints for session management, event logging,
cost analysis, and snapshot operations.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime
import logging

from core import get_db
from core.models import (
    RagSession,
    SessionDetail,
    CostBreakdown,
    StoredEvent,
    Snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["RAG Debugger"])


# Session endpoints

@router.post("/sessions", response_model=RagSession, status_code=201)
async def create_session(query: str = Body(..., embed=True)):
    """
    Create a new RAG session.
    
    Args:
        query: The user's query
        
    Returns:
        Created session
    """
    try:
        db = get_db()
        session = RagSession(query=query)
        created = db.create_session(session)
        logger.info(f"Created session {created.id}")
        return created
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[RagSession])
async def list_sessions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List recent sessions.
    
    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        
    Returns:
        List of sessions, most recent first
    """
    try:
        db = get_db()
        sessions = db.list_sessions(limit=limit, offset=offset)
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """
    Get complete session details including all events.
    
    Args:
        session_id: Session ID
        
    Returns:
        Complete session detail
    """
    try:
        db = get_db()
        session_detail = db.get_session_detail(session_id)
        
        if not session_detail:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        return session_detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sessions/{session_id}", response_model=RagSession)
async def update_session(
    session_id: str,
    completed_at: Optional[datetime] = Body(None),
    total_cost: Optional[float] = Body(None),
    total_duration_ms: Optional[int] = Body(None),
    model: Optional[str] = Body(None)
):
    """
    Update session fields.
    
    Args:
        session_id: Session ID to update
        completed_at: Completion timestamp
        total_cost: Total cost
        total_duration_ms: Total duration
        model: Model name
        
    Returns:
        Updated session
    """
    try:
        db = get_db()
        
        # Build updates dict
        updates = {}
        if completed_at is not None:
            updates['completed_at'] = completed_at
        if total_cost is not None:
            updates['total_cost'] = total_cost
        if total_duration_ms is not None:
            updates['total_duration_ms'] = total_duration_ms
        if model is not None:
            updates['model'] = model
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updated = db.update_session(session_id, **updates)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Return updated session
        session = db.get_session(session_id)
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """
    Delete a session and all its events.
    
    Args:
        session_id: Session ID to delete
    """
    try:
        db = get_db()
        deleted = db.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        logger.info(f"Deleted session {session_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Event endpoints

@router.post("/sessions/{session_id}/events", response_model=StoredEvent, status_code=201)
async def log_event(session_id: str, event: StoredEvent):
    """
    Log an event for a session.
    
    Args:
        session_id: Session ID
        event: Event to log
        
    Returns:
        Stored event
    """
    try:
        db = get_db()
        
        # Verify session exists
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Ensure event has correct session_id
        event.session_id = session_id
        
        stored = db.store_event(event)
        logger.info(f"Logged {event.event_type} event for session {session_id}")
        return stored
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging event for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cost endpoints

@router.get("/sessions/{session_id}/costs", response_model=CostBreakdown)
async def get_costs(session_id: str):
    """
    Get cost breakdown for a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Cost breakdown
    """
    try:
        db = get_db()
        
        # Verify session exists
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        cost_breakdown = db.get_cost_breakdown(session_id)
        return cost_breakdown
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting costs for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Snapshot endpoints

@router.post("/snapshots", response_model=Snapshot, status_code=201)
async def create_snapshot(
    session_id: str = Body(...),
    tags: List[str] = Body(default_factory=list)
):
    """
    Create a snapshot from a session for regression testing.
    
    Args:
        session_id: Session to snapshot
        tags: Optional tags for categorization
        
    Returns:
        Created snapshot
    """
    try:
        db = get_db()
        
        # Get session detail
        session_detail = db.get_session_detail(session_id)
        if not session_detail:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Extract chunks and answer
        chunks = []
        if session_detail.retrieval:
            chunks = [chunk.model_dump() for chunk in session_detail.retrieval.chunks]
        
        answer = ""
        if session_detail.generation:
            answer = session_detail.generation.response
        
        # Create snapshot
        snapshot = Snapshot(
            session_id=session_id,
            query=session_detail.session.query,
            chunks=chunks,
            answer=answer,
            cost=session_detail.session.total_cost or 0.0,
            tags=tags,
            model=session_detail.session.model
        )
        
        created = db.create_snapshot(snapshot)
        logger.info(f"Created snapshot {created.id} from session {session_id}")
        return created
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots", response_model=List[Snapshot])
async def list_snapshots(limit: int = Query(10, ge=1, le=100)):
    """
    List recent snapshots.
    
    Args:
        limit: Maximum number to return
        
    Returns:
        List of snapshots, most recent first
    """
    try:
        db = get_db()
        snapshots = db.list_snapshots(limit=limit)
        return snapshots
    except Exception as e:
        logger.error(f"Error listing snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}", response_model=Snapshot)
async def get_snapshot(snapshot_id: str):
    """
    Get a snapshot by ID.
    
    Args:
        snapshot_id: Snapshot ID
        
    Returns:
        Snapshot details
    """
    try:
        db = get_db()
        snapshot = db.get_snapshot(snapshot_id)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        
        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/snapshots/{snapshot_id}", status_code=204)
async def delete_snapshot(snapshot_id: str):
    """
    Delete a snapshot.
    
    Args:
        snapshot_id: Snapshot ID to delete
    """
    try:
        db = get_db()
        deleted = db.delete_snapshot(snapshot_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        
        logger.info(f"Deleted snapshot {snapshot_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/latest/id")
async def get_latest_session_id():
    """
    Get the ID of the most recent session.
    
    Useful for CLI "trace last" command.
    
    Returns:
        Dict with session_id
    """
    try:
        db = get_db()
        session = db.get_latest_session()
        
        if not session:
            raise HTTPException(status_code=404, detail="No sessions found")
        
        return {"session_id": session.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

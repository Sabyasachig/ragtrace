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
    ComparisonResult,
    PromptVersion,
    PromptVersionDiff,
)
from core.regression import compare_snapshots, score_regression

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


@router.get("/sessions/{session_id}/events", response_model=List[StoredEvent])
async def get_session_events(session_id: str):
    """
    Get all events for a session as StoredEvent objects.
    
    Args:
        session_id: Session ID
        
    Returns:
        List of StoredEvent objects for the session
    """
    try:
        db = get_db()
        
        # Verify session exists
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Query events directly from database
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT id, session_id, event_type, timestamp, data
            FROM events 
            WHERE session_id = ? 
            ORDER BY timestamp ASC
        """, (session_id,))
        
        events = []
        for row in cursor.fetchall():
            import json
            event = StoredEvent(
                id=row["id"],
                session_id=row["session_id"],
                event_type=row["event_type"],
                timestamp=row["timestamp"],
                data=json.loads(row["data"])
            )
            events.append(event)
        
        logger.info(f"Retrieved {len(events)} events for session {session_id}")
        return events
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting events for session {session_id}: {e}")
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


@router.get("/sessions/{session_id}/cost", response_model=CostBreakdown)
async def get_session_cost(session_id: str):
    """
    Get cost breakdown for a session (singular endpoint alias).
    
    Args:
        session_id: Session ID
        
    Returns:
        Cost breakdown
    """
    return await get_costs(session_id)


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


@router.get("/snapshots/{snapshot1_id}/compare/{snapshot2_id}", response_model=ComparisonResult)
async def compare_snapshots_endpoint(snapshot1_id: str, snapshot2_id: str):
    """
    Compare two snapshots for regression testing.

    Args:
        snapshot1_id: Baseline snapshot ID
        snapshot2_id: Candidate snapshot ID

    Returns:
        Full ComparisonResult with retrieval, answer and cost diffs.
    """
    try:
        db = get_db()

        snap1 = db.get_snapshot(snapshot1_id)
        if not snap1:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot1_id} not found")

        snap2 = db.get_snapshot(snapshot2_id)
        if not snap2:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot2_id} not found")

        result = compare_snapshots(snap1, snap2)
        logger.info(f"Compared snapshots {snapshot1_id} vs {snapshot2_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot1_id}/score/{snapshot2_id}")
async def score_snapshots_endpoint(snapshot1_id: str, snapshot2_id: str):
    """
    Get a regression score summary comparing two snapshots.

    Returns a concise verdict (PASS / WARN / FAIL) with per-dimension scores.
    """
    try:
        db = get_db()

        snap1 = db.get_snapshot(snapshot1_id)
        if not snap1:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot1_id} not found")

        snap2 = db.get_snapshot(snapshot2_id)
        if not snap2:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot2_id} not found")

        score = score_regression(snap1, snap2)
        return score
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring snapshots: {e}")
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


# ── Prompt Versioning endpoints ───────────────────────────────────────────────

@router.get("/prompts", response_model=List[str])
async def list_prompt_names():
    """Return all distinct prompt names in the registry."""
    try:
        db = get_db()
        return db.list_prompt_names()
    except Exception as e:
        logger.error(f"Error listing prompt names: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts", response_model=PromptVersion, status_code=201)
async def create_prompt_version(
    name: str = Body(...),
    template: str = Body(...),
    description: Optional[str] = Body(None),
    tags: List[str] = Body(default_factory=list),
):
    """
    Save a new version of a named prompt template.

    If the name already exists a new version is created; otherwise the registry
    entry is created at v1.

    Args:
        name: Logical prompt name (e.g. 'qa_template').
        template: Full prompt template text.
        description: Optional human-readable change description.
        tags: Optional tags (e.g. ['production', 'v2']).

    Returns:
        The saved PromptVersion with its auto-assigned version number.
    """
    try:
        db = get_db()
        pv = PromptVersion(name=name, version=0, template=template,
                           description=description, tags=tags)
        saved = db.save_prompt_version(pv)
        logger.info(f"Saved prompt '{name}' v{saved.version}")
        return saved
    except Exception as e:
        logger.error(f"Error saving prompt version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{name}", response_model=List[PromptVersion])
async def list_versions_for_prompt(name: str):
    """List all versions of a named prompt, newest first."""
    try:
        db = get_db()
        versions = db.list_prompt_versions(name)
        if not versions:
            raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
        return versions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing versions for prompt '{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{name}/active", response_model=PromptVersion)
async def get_active_prompt_version(name: str):
    """Return the currently active version of a named prompt."""
    try:
        db = get_db()
        pv = db.get_prompt_version(name)
        if not pv:
            raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
        return pv
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active prompt '{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{name}/versions/{version}", response_model=PromptVersion)
async def get_prompt_version(name: str, version: int):
    """Return a specific version of a named prompt."""
    try:
        db = get_db()
        pv = db.get_prompt_version(name, version)
        if not pv:
            raise HTTPException(
                status_code=404, detail=f"Prompt '{name}' v{version} not found"
            )
        return pv
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt '{name}' v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{name}/diff/{version_a}/{version_b}", response_model=PromptVersionDiff)
async def diff_prompt_versions(name: str, version_a: int, version_b: int):
    """
    Return a unified diff between two versions of a prompt template.

    Args:
        name: Prompt name.
        version_a: Baseline (older) version number.
        version_b: Candidate (newer) version number.

    Returns:
        PromptVersionDiff with diff lines and similarity score.
    """
    try:
        import difflib

        db = get_db()
        pv_a = db.get_prompt_version(name, version_a)
        if not pv_a:
            raise HTTPException(status_code=404, detail=f"Prompt '{name}' v{version_a} not found")

        pv_b = db.get_prompt_version(name, version_b)
        if not pv_b:
            raise HTTPException(status_code=404, detail=f"Prompt '{name}' v{version_b} not found")

        old_lines = pv_a.template.splitlines(keepends=True)
        new_lines = pv_b.template.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"v{version_a}", tofile=f"v{version_b}",
            lineterm="",
        ))
        similarity = difflib.SequenceMatcher(None, pv_a.template, pv_b.template).ratio()

        return PromptVersionDiff(
            name=name,
            version_old=version_a,
            version_new=version_b,
            diff_lines=diff_lines,
            similarity_score=round(similarity, 4),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error diffing prompt '{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prompts/{name}/versions/{version}", status_code=204)
async def delete_prompt_version(name: str, version: int):
    """Delete a specific version of a named prompt."""
    try:
        db = get_db()
        deleted = db.delete_prompt_version(name, version)
        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Prompt '{name}' v{version} not found"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt '{name}' v{version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


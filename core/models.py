"""
Data models for RAG Debugger.

This module defines all Pydantic models used throughout the application.
These models ensure type safety and validation for all data flows.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid4())


class ChunkMetadata(BaseModel):
    """Metadata associated with a retrieved chunk."""
    
    source: Optional[str] = Field(None, description="Source document or file")
    page: Optional[int] = Field(None, description="Page number if applicable")
    score: float = Field(..., description="Similarity or relevance score")
    document_id: Optional[str] = Field(None, description="Document identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "docs/rag_guide.pdf",
                "page": 5,
                "score": 0.92,
                "document_id": "doc_123"
            }
        }


class RetrievedChunk(BaseModel):
    """A single chunk retrieved during the retrieval phase."""
    
    text: str = Field(..., description="The actual text content of the chunk")
    metadata: ChunkMetadata = Field(..., description="Associated metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "RAG combines retrieval and generation...",
                "metadata": {
                    "source": "docs/rag_guide.pdf",
                    "page": 5,
                    "score": 0.92
                }
            }
        }


class RagSession(BaseModel):
    """
    Main session object tracking a complete RAG request.
    
    A session represents one query through the RAG pipeline, from
    retrieval through generation. It aggregates all events and costs.
    """
    
    id: str = Field(default_factory=generate_id, description="Unique session ID")
    query: str = Field(..., description="The user's query")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    completed_at: Optional[datetime] = Field(None, description="Session completion time")
    total_cost: Optional[float] = Field(None, description="Total cost in USD")
    total_duration_ms: Optional[int] = Field(None, description="Total duration in milliseconds")
    model: Optional[str] = Field(None, description="LLM model used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_abc123",
                "query": "What is RAG?",
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:03Z",
                "total_cost": 0.027,
                "total_duration_ms": 2800,
                "model": "gpt-4"
            }
        }


class RetrievalEvent(BaseModel):
    """
    Event capturing the retrieval phase.
    
    Records what chunks were retrieved, their scores, and the cost/timing
    of the embedding and search operations.
    """
    
    id: str = Field(default_factory=generate_id)
    session_id: str = Field(..., description="Associated session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    chunks: List[RetrievedChunk] = Field(..., description="Retrieved chunks")
    duration_ms: int = Field(..., description="Retrieval duration in milliseconds")
    embedding_tokens: Optional[int] = Field(None, description="Tokens used for query embedding")
    embedding_cost: float = Field(0.0, description="Cost of query embedding")
    retrieval_method: Optional[str] = Field(None, description="Retrieval method used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "event_ret_123",
                "session_id": "session_abc123",
                "timestamp": "2024-01-15T10:30:00Z",
                "chunks": [],
                "duration_ms": 120,
                "embedding_tokens": 100,
                "embedding_cost": 0.00001,
                "retrieval_method": "vector_search"
            }
        }


class PromptEvent(BaseModel):
    """
    Event capturing the prompt assembly phase.
    
    Records the final assembled prompt that will be sent to the LLM,
    including token count for cost estimation.
    """
    
    id: str = Field(default_factory=generate_id)
    session_id: str = Field(..., description="Associated session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prompt: str = Field(..., description="The assembled prompt text")
    token_count: int = Field(..., description="Number of tokens in prompt")
    template_name: Optional[str] = Field(None, description="Template used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "event_prompt_123",
                "session_id": "session_abc123",
                "timestamp": "2024-01-15T10:30:00Z",
                "prompt": "Context: ...\n\nQuestion: What is RAG?",
                "token_count": 500,
                "template_name": "qa_template"
            }
        }


class GenerationEvent(BaseModel):
    """
    Event capturing the LLM generation phase.
    
    Records the model's response, token usage, costs, and timing.
    This is typically the most expensive part of the pipeline.
    """
    
    id: str = Field(default_factory=generate_id)
    session_id: str = Field(..., description="Associated session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response: str = Field(..., description="The LLM's response")
    model: str = Field(..., description="Model name (e.g., gpt-4)")
    input_tokens: int = Field(..., description="Input tokens consumed")
    output_tokens: int = Field(..., description="Output tokens generated")
    cost: float = Field(..., description="Generation cost in USD")
    duration_ms: int = Field(..., description="Generation duration in milliseconds")
    temperature: Optional[float] = Field(None, description="Temperature setting")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "event_gen_123",
                "session_id": "session_abc123",
                "timestamp": "2024-01-15T10:30:02Z",
                "response": "RAG stands for Retrieval Augmented Generation...",
                "model": "gpt-4",
                "input_tokens": 500,
                "output_tokens": 200,
                "cost": 0.027,
                "duration_ms": 2500,
                "temperature": 0.7
            }
        }


class CostBreakdown(BaseModel):
    """
    Detailed cost breakdown for a session.
    
    Helps identify where money is being spent in the RAG pipeline.
    """
    
    session_id: str
    embedding_cost: float = Field(0.0, description="Cost of embeddings")
    input_cost: float = Field(0.0, description="Cost of input tokens")
    output_cost: float = Field(0.0, description="Cost of output tokens")
    total_cost: float = Field(0.0, description="Total cost")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "embedding_cost": 0.00001,
                "input_cost": 0.015,
                "output_cost": 0.012,
                "total_cost": 0.027
            }
        }


class SessionDetail(BaseModel):
    """
    Complete session details including all events.
    
    This is the full view of a RAG execution, used for inspection
    and debugging in the UI and CLI.
    """
    
    session: RagSession
    retrieval: Optional[RetrievalEvent] = None
    prompt: Optional[PromptEvent] = None
    generation: Optional[GenerationEvent] = None
    cost_breakdown: Optional[CostBreakdown] = None


class Snapshot(BaseModel):
    """
    A saved snapshot for regression testing.
    
    Snapshots capture the state of a RAG execution for later comparison,
    enabling detection of changes in retrieval, responses, or costs.
    """
    
    id: str = Field(default_factory=generate_id)
    session_id: str = Field(..., description="Original session ID")
    query: str = Field(..., description="The query")
    chunks: List[Dict[str, Any]] = Field(..., description="Retrieved chunks as JSON")
    answer: str = Field(..., description="The generated answer")
    cost: float = Field(..., description="Total cost")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    model: Optional[str] = Field(None, description="Model used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "snapshot_xyz789",
                "session_id": "session_abc123",
                "query": "What is RAG?",
                "chunks": [],
                "answer": "RAG is...",
                "cost": 0.027,
                "timestamp": "2024-01-15T10:30:03Z",
                "tags": ["baseline", "v1.0"],
                "model": "gpt-4"
            }
        }


class RetrievalDiff(BaseModel):
    """Difference between two retrieval results."""
    
    added: List[str] = Field(default_factory=list, description="Chunks added in new version")
    removed: List[str] = Field(default_factory=list, description="Chunks removed from old version")
    unchanged: List[str] = Field(default_factory=list, description="Chunks present in both")
    similarity_score: float = Field(..., description="Overall similarity (0-1)")


class AnswerDiff(BaseModel):
    """Difference between two answers."""
    
    diff_lines: List[str] = Field(..., description="Unified diff format")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    length_old: int = Field(..., description="Length of old answer")
    length_new: int = Field(..., description="Length of new answer")


class CostDiff(BaseModel):
    """Difference in costs between two sessions."""
    
    old_cost: float
    new_cost: float
    delta: float = Field(..., description="Cost change (positive = increase)")
    percent_change: float = Field(..., description="Percentage change")


class ComparisonResult(BaseModel):
    """Complete comparison between two snapshots."""
    
    snapshot1_id: str
    snapshot2_id: str
    query_same: bool
    retrieval_diff: RetrievalDiff
    answer_diff: AnswerDiff
    cost_diff: CostDiff
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Event type for polymorphic storage
EventType = Literal["retrieval", "prompt", "generation"]


class StoredEvent(BaseModel):
    """
    Generic event container for database storage.
    
    Since SQLite doesn't support inheritance, we store events as JSON
    with a type discriminator.
    """
    
    id: str = Field(default_factory=generate_id)
    session_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Event-specific data as JSON")

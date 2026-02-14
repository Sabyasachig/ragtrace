"""
RAG Debugger Core Module.

This module provides the core functionality for capturing, storing,
and analyzing RAG pipeline executions.
"""

from .models import (
    RagSession,
    RetrievalEvent,
    PromptEvent,
    GenerationEvent,
    RetrievedChunk,
    ChunkMetadata,
    CostBreakdown,
    SessionDetail,
    Snapshot,
    ComparisonResult,
)

from .storage import Database, get_db, close_db

from .cost import (
    CostCalculator,
    get_calculator,
    count_tokens,
    calculate_embedding_cost,
    calculate_generation_cost,
    format_cost,
)

from .capture import (
    CaptureSession,
    extract_chunks_text,
    find_unused_chunks,
    calculate_retrieval_quality,
)

__all__ = [
    # Models
    "RagSession",
    "RetrievalEvent",
    "PromptEvent",
    "GenerationEvent",
    "RetrievedChunk",
    "ChunkMetadata",
    "CostBreakdown",
    "SessionDetail",
    "Snapshot",
    "ComparisonResult",
    # Storage
    "Database",
    "get_db",
    "close_db",
    # Cost
    "CostCalculator",
    "get_calculator",
    "count_tokens",
    "calculate_embedding_cost",
    "calculate_generation_cost",
    "format_cost",
    # Capture
    "CaptureSession",
    "extract_chunks_text",
    "find_unused_chunks",
    "calculate_retrieval_quality",
]

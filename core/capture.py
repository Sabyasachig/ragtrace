"""
Event capture and aggregation for RAG Debugger.

This module provides utilities to capture and process RAG events,
extract relevant information, and prepare data for storage.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from .models import (
    RagSession,
    RetrievalEvent,
    PromptEvent,
    GenerationEvent,
    RetrievedChunk,
    ChunkMetadata,
    StoredEvent,
)
from .cost import count_tokens, calculate_embedding_cost, calculate_generation_cost

logger = logging.getLogger(__name__)


class CaptureSession:
    """
    Aggregates events for a single RAG session.
    
    This class helps collect all events (retrieval, prompt, generation)
    for a session and provides methods to extract information from
    framework-specific objects (e.g., LangChain documents).
    """
    
    def __init__(self, session_id: str, query: str):
        """
        Initialize a capture session.
        
        Args:
            session_id: Unique session identifier
            query: User query
        """
        self.session_id = session_id
        self.query = query
        self.created_at = datetime.utcnow()
        self.retrieval_event: Optional[RetrievalEvent] = None
        self.prompt_event: Optional[PromptEvent] = None
        self.generation_event: Optional[GenerationEvent] = None
    
    def capture_retrieval(
        self,
        documents: List[Any],
        duration_ms: int,
        embedding_model: str = "text-embedding-ada-002"
    ) -> RetrievalEvent:
        """
        Capture retrieval event from documents.
        
        Args:
            documents: Retrieved documents (e.g., LangChain Document objects)
            duration_ms: Duration of retrieval in milliseconds
            embedding_model: Embedding model used
            
        Returns:
            RetrievalEvent
        """
        chunks = []
        
        for doc in documents:
            # Extract text and metadata
            # This works with LangChain Document objects and dict-like objects
            if hasattr(doc, 'page_content'):
                # LangChain Document
                text = doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            elif isinstance(doc, dict):
                text = doc.get('page_content', doc.get('text', str(doc)))
                metadata = doc.get('metadata', {})
            else:
                text = str(doc)
                metadata = {}
            
            # Extract score (relevance/similarity)
            score = metadata.get('score', metadata.get('similarity', 0.0))
            if isinstance(score, (int, float)):
                score = float(score)
            else:
                score = 0.0
            
            # Build chunk
            chunk = RetrievedChunk(
                text=text,
                metadata=ChunkMetadata(
                    source=metadata.get('source'),
                    page=metadata.get('page'),
                    score=score,
                    document_id=metadata.get('doc_id', metadata.get('id'))
                )
            )
            chunks.append(chunk)
        
        # Calculate embedding cost
        query_tokens = count_tokens(self.query, "gpt-3.5-turbo")
        embedding_cost = calculate_embedding_cost(query_tokens, embedding_model)
        
        self.retrieval_event = RetrievalEvent(
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            chunks=chunks,
            duration_ms=duration_ms,
            embedding_tokens=query_tokens,
            embedding_cost=embedding_cost,
            retrieval_method="vector_search"
        )
        
        logger.debug(f"Captured retrieval: {len(chunks)} chunks, {duration_ms}ms")
        return self.retrieval_event
    
    def capture_prompt(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        template_name: Optional[str] = None
    ) -> PromptEvent:
        """
        Capture prompt assembly event.
        
        Args:
            prompt: The assembled prompt text
            model: Model for token counting
            template_name: Optional template identifier
            
        Returns:
            PromptEvent
        """
        token_count = count_tokens(prompt, model)
        
        self.prompt_event = PromptEvent(
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            prompt=prompt,
            token_count=token_count,
            template_name=template_name
        )
        
        logger.debug(f"Captured prompt: {token_count} tokens")
        return self.prompt_event
    
    def capture_generation(
        self,
        response: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        temperature: Optional[float] = None
    ) -> GenerationEvent:
        """
        Capture LLM generation event.
        
        Args:
            response: The LLM's response
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            duration_ms: Generation duration in milliseconds
            temperature: Temperature setting
            
        Returns:
            GenerationEvent
        """
        # Calculate cost
        input_cost, output_cost, total_cost = calculate_generation_cost(
            input_tokens, output_tokens, model
        )
        
        self.generation_event = GenerationEvent(
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            response=response,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            duration_ms=duration_ms,
            temperature=temperature
        )
        
        logger.debug(f"Captured generation: {output_tokens} tokens, ${total_cost:.5f}")
        return self.generation_event
    
    def get_total_duration(self) -> Optional[int]:
        """
        Calculate total pipeline duration.
        
        Returns:
            Total duration in milliseconds, or None if not all events captured
        """
        if not all([self.retrieval_event, self.generation_event]):
            return None
        
        total = 0
        if self.retrieval_event:
            total += self.retrieval_event.duration_ms
        if self.generation_event:
            total += self.generation_event.duration_ms
        
        return total
    
    def get_total_cost(self) -> float:
        """
        Calculate total cost for the session.
        
        Returns:
            Total cost in USD
        """
        total = 0.0
        
        if self.retrieval_event:
            total += self.retrieval_event.embedding_cost
        if self.generation_event:
            total += self.generation_event.cost
        
        return total
    
    def to_session(self) -> RagSession:
        """
        Convert to RagSession object.
        
        Returns:
            RagSession with aggregated metadata
        """
        return RagSession(
            id=self.session_id,
            query=self.query,
            created_at=self.created_at,
            completed_at=datetime.utcnow(),
            total_cost=self.get_total_cost(),
            total_duration_ms=self.get_total_duration(),
            model=self.generation_event.model if self.generation_event else None
        )
    
    def to_stored_events(self) -> List[StoredEvent]:
        """
        Convert captured events to storable format.
        
        Returns:
            List of StoredEvent objects
        """
        events = []
        
        if self.retrieval_event:
            events.append(StoredEvent(
                session_id=self.session_id,
                event_type="retrieval",
                timestamp=self.retrieval_event.timestamp,
                data=self.retrieval_event.model_dump()
            ))
        
        if self.prompt_event:
            events.append(StoredEvent(
                session_id=self.session_id,
                event_type="prompt",
                timestamp=self.prompt_event.timestamp,
                data=self.prompt_event.model_dump()
            ))
        
        if self.generation_event:
            events.append(StoredEvent(
                session_id=self.session_id,
                event_type="generation",
                timestamp=self.generation_event.timestamp,
                data=self.generation_event.model_dump()
            ))
        
        return events


def extract_chunks_text(chunks: List[RetrievedChunk]) -> List[str]:
    """
    Extract just the text from chunks.
    
    Args:
        chunks: List of RetrievedChunk objects
        
    Returns:
        List of chunk text strings
    """
    return [chunk.text for chunk in chunks]


def find_unused_chunks(
    chunks: List[RetrievedChunk],
    prompt: str
) -> List[RetrievedChunk]:
    """
    Identify chunks that were retrieved but not used in the prompt.
    
    This helps identify wasted retrieval effort.
    
    Args:
        chunks: Retrieved chunks
        prompt: The assembled prompt
        
    Returns:
        List of chunks not found in the prompt
    """
    unused = []
    
    for chunk in chunks:
        # Simple substring check
        # TODO: Could be made more sophisticated with semantic similarity
        if chunk.text not in prompt:
            unused.append(chunk)
    
    return unused


def calculate_retrieval_quality(chunks: List[RetrievedChunk]) -> Dict[str, Any]:
    """
    Calculate quality metrics for retrieval.
    
    Args:
        chunks: Retrieved chunks
        
    Returns:
        Dictionary with quality metrics
    """
    if not chunks:
        return {
            "num_chunks": 0,
            "avg_score": 0.0,
            "max_score": 0.0,
            "min_score": 0.0,
        }
    
    scores = [chunk.metadata.score for chunk in chunks]
    
    return {
        "num_chunks": len(chunks),
        "avg_score": sum(scores) / len(scores),
        "max_score": max(scores),
        "min_score": min(scores),
        "score_variance": max(scores) - min(scores),
    }

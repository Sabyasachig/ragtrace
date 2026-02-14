"""
Unit tests for capture module.

Tests event capture and aggregation functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from core.capture import CaptureSession, extract_chunks_text, detect_unused_chunks
from core.models import RetrievedChunk, ChunkMetadata


class MockDocument:
    """Mock LangChain Document for testing."""
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class TestCaptureSession:
    """Test CaptureSession class."""
    
    def test_init(self):
        """Test session initialization."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        assert session.session_id == "test-123"
        assert session.query == "What is RAG?"
        assert session.retrieval_event is None
        assert session.prompt_event is None
        assert session.generation_event is None
    
    def test_capture_retrieval_langchain_docs(self):
        """Test capturing retrieval with LangChain documents."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Create mock LangChain documents
        docs = [
            MockDocument(
                "RAG is Retrieval-Augmented Generation",
                {"source": "doc1.txt", "page": 1, "score": 0.95}
            ),
            MockDocument(
                "It combines retrieval with generation",
                {"source": "doc2.txt", "page": 2, "score": 0.88}
            ),
        ]
        
        event = session.capture_retrieval(docs, duration_ms=150)
        
        assert event is not None
        assert len(event.chunks) == 2
        assert event.duration_ms == 150
        assert event.chunks[0].text == "RAG is Retrieval-Augmented Generation"
        assert event.chunks[0].metadata.score == 0.95
    
    def test_capture_retrieval_dict_docs(self):
        """Test capturing retrieval with dict documents."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Create dict-style documents
        docs = [
            {
                "page_content": "RAG is powerful",
                "metadata": {"source": "doc1.txt", "score": 0.9}
            },
        ]
        
        event = session.capture_retrieval(docs, duration_ms=100)
        
        assert event is not None
        assert len(event.chunks) == 1
        assert event.chunks[0].text == "RAG is powerful"
    
    def test_capture_retrieval_empty_docs(self):
        """Test capturing retrieval with no documents."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        event = session.capture_retrieval([], duration_ms=50)
        
        assert event is not None
        assert len(event.chunks) == 0
        assert event.duration_ms == 50
    
    def test_capture_prompt(self):
        """Test capturing prompt event."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        prompt_text = "Context: RAG info\n\nQuestion: What is RAG?"
        event = session.capture_prompt(prompt_text, model="gpt-4")
        
        assert event is not None
        assert event.prompt == prompt_text
        assert event.token_count > 0
    
    def test_capture_prompt_with_template(self):
        """Test capturing prompt with template name."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        prompt_text = "Question: What is RAG?"
        event = session.capture_prompt(
            prompt_text, 
            model="gpt-3.5-turbo",
            template_name="simple_qa"
        )
        
        assert event is not None
        assert event.template_name == "simple_qa"
    
    def test_capture_generation(self):
        """Test capturing generation event."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        event = session.capture_generation(
            response="RAG is Retrieval-Augmented Generation",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            duration_ms=1500,
            temperature=0.7
        )
        
        assert event is not None
        assert event.response == "RAG is Retrieval-Augmented Generation"
        assert event.model == "gpt-4"
        assert event.input_tokens == 100
        assert event.output_tokens == 50
        assert event.duration_ms == 1500
        assert event.temperature == 0.7
        assert event.cost > 0
    
    def test_get_total_duration_complete(self):
        """Test getting total duration with all events."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Capture events
        docs = [MockDocument("Test content", {})]
        session.capture_retrieval(docs, duration_ms=150)
        session.capture_generation(
            "Response", "gpt-4", 100, 50, duration_ms=1500
        )
        
        total = session.get_total_duration()
        assert total == 1650  # 150 + 1500
    
    def test_get_total_duration_incomplete(self):
        """Test getting total duration with missing events."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Only capture retrieval
        docs = [MockDocument("Test content", {})]
        session.capture_retrieval(docs, duration_ms=150)
        
        total = session.get_total_duration()
        assert total is None  # Not all events captured
    
    def test_get_total_cost(self):
        """Test getting total cost."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Capture events with costs
        docs = [MockDocument("Test content", {})]
        session.capture_retrieval(docs, duration_ms=150)
        session.capture_generation(
            "Response", "gpt-4", 100, 50, duration_ms=1500
        )
        
        total = session.get_total_cost()
        assert total > 0
        assert isinstance(total, float)
    
    def test_get_total_cost_no_events(self):
        """Test getting total cost with no events."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        total = session.get_total_cost()
        assert total == 0.0
    
    def test_to_session(self):
        """Test converting to RagSession."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Capture some events
        docs = [MockDocument("Test content", {})]
        session.capture_retrieval(docs, duration_ms=150)
        session.capture_generation(
            "Response", "gpt-4", 100, 50, duration_ms=1500
        )
        
        rag_session = session.to_session()
        assert rag_session.id == "test-123"
        assert rag_session.query == "What is RAG?"
        assert rag_session.model == "gpt-4"
        assert rag_session.total_cost > 0
        assert rag_session.total_duration_ms == 1650
    
    def test_to_stored_events(self):
        """Test converting to stored events."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Capture all event types
        docs = [MockDocument("Test content", {})]
        session.capture_retrieval(docs, duration_ms=150)
        session.capture_prompt("Test prompt")
        session.capture_generation(
            "Response", "gpt-4", 100, 50, duration_ms=1500
        )
        
        stored_events = session.to_stored_events()
        assert len(stored_events) == 3
        
        event_types = [e.event_type for e in stored_events]
        assert "retrieval" in event_types
        assert "prompt" in event_types
        assert "generation" in event_types
    
    def test_to_stored_events_partial(self):
        """Test converting to stored events with only some events."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        # Only capture retrieval
        docs = [MockDocument("Test content", {})]
        session.capture_retrieval(docs, duration_ms=150)
        
        stored_events = session.to_stored_events()
        assert len(stored_events) == 1
        assert stored_events[0].event_type == "retrieval"


class TestExtractChunksText:
    """Test extract_chunks_text utility function."""
    
    def test_extract_simple(self):
        """Test extracting text from chunks."""
        chunks = [
            RetrievedChunk(
                text="First chunk",
                metadata=ChunkMetadata(source="doc1.txt", score=0.9)
            ),
            RetrievedChunk(
                text="Second chunk",
                metadata=ChunkMetadata(source="doc2.txt", score=0.8)
            ),
        ]
        
        texts = extract_chunks_text(chunks)
        assert len(texts) == 2
        assert texts[0] == "First chunk"
        assert texts[1] == "Second chunk"
    
    def test_extract_empty(self):
        """Test extracting from empty list."""
        texts = extract_chunks_text([])
        assert len(texts) == 0


class TestDetectUnusedChunks:
    """Test detect_unused_chunks utility function."""
    
    def test_detect_all_used(self):
        """Test when all chunks are used."""
        chunks = [
            RetrievedChunk(
                text="RAG stands for Retrieval-Augmented Generation",
                metadata=ChunkMetadata(source="doc1.txt", score=0.9)
            ),
        ]
        response = "According to the context, RAG stands for Retrieval-Augmented Generation"
        
        unused = detect_unused_chunks(chunks, response)
        assert len(unused) == 0
    
    def test_detect_some_unused(self):
        """Test when some chunks are unused."""
        chunks = [
            RetrievedChunk(
                text="RAG is powerful",
                metadata=ChunkMetadata(source="doc1.txt", score=0.9)
            ),
            RetrievedChunk(
                text="Unrelated content about cats",
                metadata=ChunkMetadata(source="doc2.txt", score=0.5)
            ),
        ]
        response = "RAG is very powerful for question answering"
        
        unused = detect_unused_chunks(chunks, response)
        # The cat content should be unused
        assert len(unused) >= 1
    
    def test_detect_empty_chunks(self):
        """Test with no chunks."""
        unused = detect_unused_chunks([], "Some response")
        assert len(unused) == 0
    
    def test_detect_empty_response(self):
        """Test with empty response."""
        chunks = [
            RetrievedChunk(
                text="Test content",
                metadata=ChunkMetadata(source="doc1.txt", score=0.9)
            ),
        ]
        
        unused = detect_unused_chunks(chunks, "")
        # All chunks should be unused
        assert len(unused) == 1


class TestDocumentExtraction:
    """Test extraction from different document formats."""
    
    def test_langchain_document(self):
        """Test extracting from LangChain document."""
        session = CaptureSession(session_id="test-123", query="Test")
        
        doc = MockDocument(
            "Test content",
            {"source": "test.txt", "page": 1}
        )
        
        event = session.capture_retrieval([doc], duration_ms=100)
        assert len(event.chunks) == 1
        assert event.chunks[0].text == "Test content"
        assert event.chunks[0].metadata.source == "test.txt"
        assert event.chunks[0].metadata.page == 1
    
    def test_dict_document(self):
        """Test extracting from dict."""
        session = CaptureSession(session_id="test-123", query="Test")
        
        doc = {
            "page_content": "Test content",
            "metadata": {"source": "test.txt"}
        }
        
        event = session.capture_retrieval([doc], duration_ms=100)
        assert len(event.chunks) == 1
        assert event.chunks[0].text == "Test content"
    
    def test_string_document(self):
        """Test extracting from plain string."""
        session = CaptureSession(session_id="test-123", query="Test")
        
        doc = "Just a plain string"
        
        event = session.capture_retrieval([doc], duration_ms=100)
        assert len(event.chunks) == 1
        assert event.chunks[0].text == "Just a plain string"
    
    def test_mixed_documents(self):
        """Test extracting from mixed document types."""
        session = CaptureSession(session_id="test-123", query="Test")
        
        docs = [
            MockDocument("LangChain doc", {}),
            {"page_content": "Dict doc"},
            "String doc"
        ]
        
        event = session.capture_retrieval(docs, duration_ms=100)
        assert len(event.chunks) == 3


class TestCostCalculations:
    """Test cost calculations in capture."""
    
    def test_retrieval_cost(self):
        """Test that retrieval calculates embedding cost."""
        session = CaptureSession(session_id="test-123", query="What is RAG?")
        
        docs = [MockDocument("Test", {})]
        event = session.capture_retrieval(docs, duration_ms=100)
        
        assert event.embedding_cost > 0
        assert event.embedding_tokens > 0
    
    def test_generation_cost(self):
        """Test that generation calculates model cost."""
        session = CaptureSession(session_id="test-123", query="Test")
        
        event = session.capture_generation(
            response="Test response",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            duration_ms=1000
        )
        
        assert event.cost > 0
    
    def test_total_cost_aggregation(self):
        """Test that total cost aggregates correctly."""
        session = CaptureSession(session_id="test-123", query="Test")
        
        # Capture both events
        docs = [MockDocument("Test", {})]
        session.capture_retrieval(docs, duration_ms=100)
        session.capture_generation(
            "Response", "gpt-4", 100, 50, duration_ms=1000
        )
        
        total = session.get_total_cost()
        embedding_cost = session.retrieval_event.embedding_cost
        generation_cost = session.generation_event.cost
        
        assert total == embedding_cost + generation_cost


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

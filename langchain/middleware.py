"""
LangChain middleware for RAG Debugger.

This module provides callback handlers that integrate with LangChain
to automatically capture RAG pipeline events.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import time
import logging

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import Document

from core import CaptureSession, get_db
from core.models import RagSession, StoredEvent

logger = logging.getLogger(__name__)


class RagDebuggerCallback(BaseCallbackHandler):
    """
    LangChain callback handler for RAG debugging.
    
    This handler intercepts LangChain events and captures:
    - Retrieval: Documents retrieved from vector stores
    - Prompts: Assembled prompts sent to LLMs
    - Generation: LLM responses and token usage
    
    Usage:
        handler = RagDebuggerCallback(session_id="my-session", query="What is RAG?")
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            callbacks=[handler]
        )
        result = chain.run("What is RAG?")
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        query: Optional[str] = None,
        api_url: Optional[str] = None,
        auto_save: bool = True
    ):
        """
        Initialize the callback handler.
        
        Args:
            session_id: Unique session identifier (auto-generated if None)
            query: User query (can be set later)
            api_url: API URL for remote logging (None for local DB)
            auto_save: Automatically save to database after completion
        """
        super().__init__()
        self.session_id = session_id
        self.query = query
        self.api_url = api_url
        self.auto_save = auto_save
        
        # Timing trackers
        self._retrieval_start: Optional[float] = None
        self._generation_start: Optional[float] = None
        
        # Captured data
        self._documents: List[Document] = []
        self._prompts: List[str] = []
        self._responses: List[str] = []
        self._llm_outputs: List[Dict[str, Any]] = []
        
        # Capture session
        self._capture: Optional[CaptureSession] = None
        
        logger.debug(f"RagDebuggerCallback initialized with session_id={session_id}")
    
    def _ensure_capture_session(self):
        """Ensure capture session is initialized."""
        if self._capture is None:
            if not self.query:
                logger.warning("Query not set, using placeholder")
                self.query = "Unknown query"
            
            if not self.session_id:
                # Create a session in DB to get ID
                db = get_db()
                session = RagSession(query=self.query)
                created = db.create_session(session)
                self.session_id = created.id
                logger.info(f"Created session {self.session_id}")
            
            self._capture = CaptureSession(
                session_id=self.session_id,
                query=self.query
            )
    
    # Retriever callbacks
    
    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        **kwargs: Any
    ) -> None:
        """Called when retriever starts."""
        logger.debug(f"Retriever started for query: {query}")
        self._retrieval_start = time.time()
        
        # Update query if not set
        if not self.query:
            self.query = query
    
    def on_retriever_end(
        self,
        documents: List[Document],
        **kwargs: Any
    ) -> None:
        """
        Called when retriever finishes.
        
        Captures the retrieved documents and their metadata.
        """
        duration_ms = 0
        if self._retrieval_start:
            duration_ms = int((time.time() - self._retrieval_start) * 1000)
        
        logger.info(f"Retriever completed: {len(documents)} documents in {duration_ms}ms")
        
        self._documents = documents
        self._ensure_capture_session()
        
        # Capture retrieval event
        try:
            self._capture.capture_retrieval(
                documents=documents,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"Error capturing retrieval: {e}", exc_info=True)
    
    def on_retriever_error(
        self,
        error: BaseException,
        **kwargs: Any
    ) -> None:
        """Called when retriever encounters an error."""
        logger.error(f"Retriever error: {error}")
    
    # LLM callbacks
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """
        Called when LLM starts generation.
        
        Captures the prompt that will be sent to the LLM.
        """
        logger.debug(f"LLM started with {len(prompts)} prompt(s)")
        self._generation_start = time.time()
        self._prompts.extend(prompts)
        
        self._ensure_capture_session()
        
        # Capture prompt event
        if prompts:
            try:
                model = self._extract_model_name(serialized)
                self._capture.capture_prompt(
                    prompt=prompts[0],
                    model=model
                )
            except Exception as e:
                logger.error(f"Error capturing prompt: {e}", exc_info=True)
    
    def on_llm_end(
        self,
        response: Any,
        **kwargs: Any
    ) -> None:
        """
        Called when LLM finishes generation.
        
        Captures the response, token usage, and costs.
        """
        duration_ms = 0
        if self._generation_start:
            duration_ms = int((time.time() - self._generation_start) * 1000)
        
        logger.info(f"LLM completed in {duration_ms}ms")
        
        self._ensure_capture_session()
        
        try:
            # Extract response text
            if hasattr(response, 'generations') and response.generations:
                generation = response.generations[0][0]
                response_text = generation.text if hasattr(generation, 'text') else str(generation)
                self._responses.append(response_text)
            else:
                response_text = str(response)
                self._responses.append(response_text)
            
            # Extract token usage and model info
            llm_output = {}
            if hasattr(response, 'llm_output') and response.llm_output:
                llm_output = response.llm_output
                self._llm_outputs.append(llm_output)
            
            # Get token counts
            token_usage = llm_output.get('token_usage', {})
            input_tokens = token_usage.get('prompt_tokens', 0)
            output_tokens = token_usage.get('completion_tokens', 0)
            model = llm_output.get('model_name', 'gpt-3.5-turbo')
            
            # If token usage not available, estimate from text
            if not input_tokens and self._prompts:
                from core.cost import count_tokens
                input_tokens = count_tokens(self._prompts[0], model)
            if not output_tokens:
                from core.cost import count_tokens
                output_tokens = count_tokens(response_text, model)
            
            # Capture generation event
            self._capture.capture_generation(
                response=response_text,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms
            )
            
            # Auto-save if enabled
            if self.auto_save:
                self.save()
        
        except Exception as e:
            logger.error(f"Error capturing generation: {e}", exc_info=True)
    
    def on_llm_error(
        self,
        error: BaseException,
        **kwargs: Any
    ) -> None:
        """Called when LLM encounters an error."""
        logger.error(f"LLM error: {error}")
    
    # Chain callbacks (optional, for additional context)
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain starts."""
        logger.debug("Chain started")
        
        # Try to extract query from inputs
        if not self.query:
            if 'query' in inputs:
                self.query = inputs['query']
            elif 'question' in inputs:
                self.query = inputs['question']
            elif 'input' in inputs:
                self.query = inputs['input']
    
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain completes."""
        logger.debug("Chain completed")
    
    def on_chain_error(
        self,
        error: BaseException,
        **kwargs: Any
    ) -> None:
        """Called when chain encounters an error."""
        logger.error(f"Chain error: {error}")
    
    # Utility methods
    
    def _extract_model_name(self, serialized: Dict[str, Any]) -> str:
        """Extract model name from serialized LLM config."""
        # Try various common keys
        for key in ['model_name', 'model', 'name']:
            if key in serialized:
                return serialized[key]
        
        # Check in kwargs
        if 'kwargs' in serialized:
            kwargs = serialized['kwargs']
            for key in ['model_name', 'model']:
                if key in kwargs:
                    return kwargs[key]
        
        # Default
        return 'gpt-3.5-turbo'
    
    def save(self):
        """
        Save captured events to database.
        
        This is called automatically if auto_save=True, or can be
        called manually.
        """
        if not self._capture:
            logger.warning("No capture session to save")
            return
        
        try:
            db = get_db()
            
            # Update session with final metadata
            session = self._capture.to_session()
            db.update_session(
                session.id,
                completed_at=session.completed_at,
                total_cost=session.total_cost,
                total_duration_ms=session.total_duration_ms,
                model=session.model
            )
            
            # Store all events
            for event in self._capture.to_stored_events():
                db.store_event(event)
            
            logger.info(f"Saved session {self.session_id} to database")
        
        except Exception as e:
            logger.error(f"Error saving to database: {e}", exc_info=True)
    
    def get_session_id(self) -> Optional[str]:
        """Get the session ID for this callback."""
        return self.session_id
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the captured session.
        
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "session_id": self.session_id,
            "query": self.query,
            "documents_retrieved": len(self._documents),
            "prompts_sent": len(self._prompts),
            "responses_received": len(self._responses),
        }
        
        if self._capture:
            summary.update({
                "total_cost": self._capture.get_total_cost(),
                "total_duration_ms": self._capture.get_total_duration(),
            })
        
        return summary


class SimpleRagDebugger:
    """
    Simplified interface for quick debugging.
    
    Usage:
        with SimpleRagDebugger("What is RAG?") as debugger:
            result = chain.run("What is RAG?")
        
        print(f"Session ID: {debugger.session_id}")
        print(f"Cost: ${debugger.cost:.4f}")
    """
    
    def __init__(self, query: str):
        """
        Initialize simple debugger.
        
        Args:
            query: User query
        """
        self.query = query
        self.callback = RagDebuggerCallback(query=query, auto_save=True)
        self.session_id = None
        self.cost = 0.0
    
    def __enter__(self):
        """Context manager entry."""
        return self.callback
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save session."""
        if exc_type is None:
            self.callback.save()
            self.session_id = self.callback.get_session_id()
            summary = self.callback.get_summary()
            self.cost = summary.get('total_cost', 0.0)
        return False

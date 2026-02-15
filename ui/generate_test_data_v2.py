#!/usr/bin/env python3
"""
Generate proper test data for Day 7 timeline visualizations.
Creates sessions with retrieval, prompt, and generation events.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import get_db
from core.models import (
    RagSession,
    StoredEvent,
    RetrievalEvent,
    PromptEvent,
    GenerationEvent,
    RetrievedChunk,
    ChunkMetadata
)
from datetime import datetime, timedelta
import random

def generate_test_data():
    """Generate 5 test sessions with complete event data for charts."""
    db = get_db()
    
    print("🔨 Generating Day 7 Test Data...")
    print("=" * 60)
    
    queries = [
        "What is RAG in machine learning?",
        "How does vector similarity search work?",
        "Explain the difference between GPT-3.5 and GPT-4",
        "What are embeddings in NLP?",
        "How to optimize costs in LLM applications?"
    ]
    
    models = ["gpt-4", "gpt-3.5-turbo", "gpt-4"]
    
    for i, query in enumerate(queries):
        # Create session
        session = RagSession(query=query, model=models[i % len(models)])
        created_session = db.create_session(session)
        session_id = created_session.id
        
        base_time = datetime.utcnow() - timedelta(hours=i)
        
        # 1. Create Retrieval Event
        chunks = []
        for j in range(3):
            metadata = ChunkMetadata(
                source=f"document_{j+1}.pdf",
                page=j + 1,
                score=0.95 - (j * 0.1),
                document_id=f"doc_{j+1}"
            )
            chunk = RetrievedChunk(
                text=f"This is retrieved chunk {j+1} about {query[:30]}... Contains relevant information.",
                metadata=metadata
            )
            chunks.append(chunk)
        
        retrieval_event = RetrievalEvent(
            session_id=session_id,
            timestamp=base_time,
            chunks=chunks,
            duration_ms=random.randint(100, 300),
            embedding_tokens=50,
            embedding_cost=0.00002,
            retrieval_method="vector_search"
        )
        
        # Store as StoredEvent
        retrieval_stored = StoredEvent(
            id=retrieval_event.id,
            session_id=session_id,
            event_type="retrieval",
            timestamp=retrieval_event.timestamp,
            data=retrieval_event.model_dump(mode='json')
        )
        db.store_event(retrieval_stored)
        
        # 2. Create Prompt Event
        prompt_time = base_time + timedelta(milliseconds=retrieval_event.duration_ms)
        prompt_text = f"""Context:
{chunks[0].text}
{chunks[1].text}
{chunks[2].text}

Question: {query}

Please provide a comprehensive answer based on the context above."""
        
        prompt_event = PromptEvent(
            session_id=session_id,
            timestamp=prompt_time,
            prompt=prompt_text,
            token_count=random.randint(400, 600),
            template_name="qa_with_context"
        )
        
        prompt_stored = StoredEvent(
            id=prompt_event.id,
            session_id=session_id,
            event_type="prompt",
            timestamp=prompt_event.timestamp,
            data=prompt_event.model_dump(mode='json')
        )
        db.store_event(prompt_stored)
        
        # 3. Create Generation Event
        gen_time = prompt_time + timedelta(milliseconds=50)
        input_tokens = prompt_event.token_count
        output_tokens = random.randint(150, 300)
        duration_ms = random.randint(800, 2000)
        
        # Calculate costs based on model
        model = models[i % len(models)]
        if model == "gpt-4":
            input_cost = (input_tokens / 1000) * 0.03
            output_cost = (output_tokens / 1000) * 0.06
        else:  # gpt-3.5-turbo
            input_cost = (input_tokens / 1000) * 0.0015
            output_cost = (output_tokens / 1000) * 0.002
        
        total_cost = input_cost + output_cost + retrieval_event.embedding_cost
        
        generation_event = GenerationEvent(
            session_id=session_id,
            timestamp=gen_time,
            response=f"Based on the provided context, here's a comprehensive answer to '{query}': [Generated response with detailed explanation...]",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=input_cost + output_cost,
            duration_ms=duration_ms,
            temperature=0.7
        )
        
        generation_stored = StoredEvent(
            id=generation_event.id,
            session_id=session_id,
            event_type="generation",
            timestamp=generation_event.timestamp,
            data=generation_event.model_dump(mode='json')
        )
        db.store_event(generation_stored)
        
        # Update session with totals
        total_duration = retrieval_event.duration_ms + duration_ms
        db.update_session(
            session_id,
            completed_at=gen_time + timedelta(milliseconds=duration_ms),
            total_cost=total_cost,
            total_duration_ms=total_duration,
            model=model
        )
        
        print(f"✓ Session {i+1}/5: {session_id[:12]}...")
        print(f"  - Query: {query[:50]}...")
        print(f"  - Events: retrieval (3 chunks), prompt ({input_tokens} tokens), generation ({output_tokens} tokens)")
        print(f"  - Cost: ${total_cost:.4f} | Duration: {total_duration}ms")
        print()
    
    print("=" * 60)
    print("✅ Test data generated successfully!")
    print(f"📊 Database: {db.db_path}")
    print()
    print("Next steps:")
    print("  1. Servers should already be running")
    print("  2. Open: http://localhost:3000")
    print("  3. Click on any session to see charts!")

if __name__ == "__main__":
    try:
        generate_test_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

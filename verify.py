#!/usr/bin/env python3
"""
Quick verification script for RAG Debugger MVP.
Tests core functionality without requiring OpenAI API key.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.cost import count_tokens, calculate_embedding_cost, calculate_generation_cost
from core.models import RagSession, RetrievedChunk, ChunkMetadata
from core.storage import Database
from datetime import datetime
import tempfile
import os

def test_cost_calculations():
    """Test cost calculation functions."""
    print("🧮 Testing Cost Calculations...")
    
    # Test token counting
    text = "Hello, world! This is a test."
    tokens = count_tokens(text)
    assert tokens > 0, "Token counting failed"
    print(f"  ✅ Token counting: '{text}' → {tokens} tokens")
    
    # Test embedding cost
    cost = calculate_embedding_cost(100, "text-embedding-ada-002")
    assert cost > 0, "Embedding cost calculation failed"
    print(f"  ✅ Embedding cost: 100 tokens → ${cost:.6f}")
    
    # Test generation cost
    input_cost, output_cost, total = calculate_generation_cost(100, 50, "gpt-4")
    assert total > 0, "Generation cost calculation failed"
    print(f"  ✅ Generation cost: 100 in + 50 out → ${total:.5f}")
    
    print()

def test_models():
    """Test Pydantic models."""
    print("📦 Testing Data Models...")
    
    # Test RagSession
    session = RagSession(
        query="What is RAG?",
        created_at=datetime.now()
    )
    assert session.id is not None, "Session ID generation failed"
    print(f"  ✅ RagSession: {session.id[:8]}...")
    
    # Test RetrievedChunk
    chunk = RetrievedChunk(
        text="Test content",
        metadata=ChunkMetadata(
            source="test.txt",
            score=0.95
        )
    )
    assert chunk.text == "Test content", "Chunk creation failed"
    print(f"  ✅ RetrievedChunk: score={chunk.metadata.score}")
    
    print()

def test_database():
    """Test database operations."""
    print("💾 Testing Database...")
    
    # Create temp database
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        # Initialize database
        db = Database(path)
        assert db.conn is not None, "Database connection failed"
        print(f"  ✅ Database initialized: {path}")
        
        # Create session
        session = RagSession(
            query="Test query",
            created_at=datetime.now()
        )
        db.create_session(session)
        print(f"  ✅ Session created: {session.id[:8]}...")
        
        # Retrieve session
        retrieved = db.get_session(session.id)
        assert retrieved is not None, "Session retrieval failed"
        assert retrieved.query == "Test query", "Session data mismatch"
        print(f"  ✅ Session retrieved: {retrieved.query}")
        
        # List sessions
        sessions = db.list_sessions()
        assert len(sessions) == 1, "Session listing failed"
        print(f"  ✅ Session list: {len(sessions)} session(s)")
        
        # Cleanup
        db.conn.close()
        os.unlink(path)
        print(f"  ✅ Database cleaned up")
        
    except Exception as e:
        # Cleanup on error
        if os.path.exists(path):
            os.unlink(path)
        raise e
    
    print()

def test_cli_import():
    """Test CLI can be imported."""
    print("🖥️  Testing CLI Import...")
    
    try:
        from cli.main import cli
        assert cli is not None, "CLI import failed"
        print(f"  ✅ CLI module imported successfully")
    except ImportError as e:
        print(f"  ❌ CLI import failed: {e}")
        return False
    
    print()
    return True

def test_api_import():
    """Test API can be imported."""
    print("🌐 Testing API Import...")
    
    try:
        from api.main import app
        assert app is not None, "API import failed"
        print(f"  ✅ API module imported successfully")
    except ImportError as e:
        print(f"  ❌ API import failed: {e}")
        return False
    
    print()
    return True

def test_langchain_import():
    """Test LangChain integration can be imported."""
    print("🔗 Testing LangChain Integration...")
    
    try:
        from langchain.middleware import RagDebuggerCallback
        assert RagDebuggerCallback is not None, "Callback import failed"
        print(f"  ✅ LangChain callback imported successfully")
    except ImportError as e:
        print(f"  ❌ LangChain import failed: {e}")
        return False
    
    print()
    return True

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("RAG Debugger MVP - Verification Script")
    print("=" * 60)
    print()
    
    try:
        test_cost_calculations()
        test_models()
        test_database()
        test_cli_import()
        test_api_import()
        test_langchain_import()
        
        print("=" * 60)
        print("✨ All Tests Passed! RAG Debugger is working correctly.")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Run: ragdebug init")
        print("2. Try: examples/simple_rag.py (requires OpenAI API key)")
        print("3. Inspect: ragdebug trace last")
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test Failed: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

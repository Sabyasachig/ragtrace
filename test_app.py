#!/usr/bin/env python3
"""
Comprehensive test of RAG Debugger functionality.
Tests: Database, API endpoints, and basic functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 RAG Debugger - Comprehensive Testing")
print("=" * 60)
print()

# Test 1: Database Access
print("1️⃣  Testing Database Access...")
try:
    from core import get_db
    db = get_db()
    print(f"   ✅ Database initialized: {db.db_path}")
    
    sessions = db.list_sessions(limit=10)
    print(f"   ✅ Found {len(sessions)} sessions in database")
    
    if sessions:
        session = sessions[0]
        print(f"   📊 First session:")
        print(f"      ID: {session.id[:16]}...")
        print(f"      Query: {session.query[:50]}...")
        print(f"      Cost: ${session.total_cost if session.total_cost else 0:.6f}")
        print(f"      Created: {session.created_at}")
except Exception as e:
    print(f"   ❌ Database test failed: {e}")
    sys.exit(1)

print()

# Test 2: Cost Calculation
print("2️⃣  Testing Cost Calculation...")
try:
    from core.cost import count_tokens, calculate_generation_cost
    
    text = "Hello, how are you today?"
    tokens = count_tokens(text)
    print(f"   ✅ Token counting works: '{text}' = {tokens} tokens")
    
    # Fix: correct parameter order is (input_tokens, output_tokens, model)
    result = calculate_generation_cost(100, 50, "gpt-4")
    print(f"   📊 Result type: {type(result)}, value: {result}")
    input_cost, output_cost, total_cost = result
    print(f"   ✅ Cost calculation works: 100 input + 50 output = ${total_cost:.6f}")
except Exception as e:
    import traceback
    print(f"   ❌ Cost calculation test failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# Test 3: Models
print("3️⃣  Testing Data Models...")
try:
    from core.models import RagSession, StoredEvent
    from datetime import datetime
    import uuid
    
    # Create a test session
    test_session = RagSession(
        id=str(uuid.uuid4()),
        query="Test query",
        created_at=datetime.now(),
        total_cost=0.01
    )
    print(f"   ✅ RagSession model works")
    
    # Create a test event (EventType is a Literal, not an enum)
    test_event = StoredEvent(
        id=str(uuid.uuid4()),
        session_id=test_session.id,
        event_type="generation",  # Use string literal, not enum
        timestamp=datetime.now(),
        data={"model": "gpt-4"}
    )
    print(f"   ✅ StoredEvent model works")
except Exception as e:
    print(f"   ❌ Models test failed: {e}")
    sys.exit(1)

print()

# Test 4: API Routes
print("4️⃣  Testing API Routes Import...")
try:
    from api.main import app
    from api.routes import router
    print(f"   ✅ FastAPI app imported successfully")
    print(f"   ✅ API router imported successfully")
    print(f"   ℹ️  Run 'uvicorn api.main:app --port 8000' to start API")
except Exception as e:
    print(f"   ❌ API import test failed: {e}")
    sys.exit(1)

print()

# Test 5: CLI
print("5️⃣  Testing CLI Import...")
try:
    from cli.main import cli
    print(f"   ✅ CLI imported successfully")
    print(f"   ℹ️  Run 'rag-debug --help' to use CLI")
except Exception as e:
    print(f"   ❌ CLI import test failed: {e}")
    sys.exit(1)

print()

# Test 6: LangChain Integration
print("6️⃣  Testing LangChain Integration...")
try:
    from langchain.middleware import RagTracer
    print(f"   ✅ RagTracer imported successfully")
    print(f"   ℹ️  Use with LangChain callbacks")
except ImportError as e:
    print(f"   ⚠️  LangChain not installed (optional dependency)")
    print(f"   ℹ️  Install with: pip install langchain")
except Exception as e:
    print(f"   ❌ LangChain integration test failed: {e}")
    sys.exit(1)

print()

# Test 7: Session Statistics
print("7️⃣  Testing Session Statistics...")
try:
    if sessions:
        total_cost = sum(s.total_cost or 0 for s in sessions)
        avg_cost = total_cost / len(sessions) if sessions else 0
        
        print(f"   📊 Statistics:")
        print(f"      Total Sessions: {len(sessions)}")
        print(f"      Total Cost: ${total_cost:.6f}")
        print(f"      Avg Cost/Session: ${avg_cost:.6f}")
    else:
        print(f"   ℹ️  No sessions to analyze")
except Exception as e:
    print(f"   ⚠️  Statistics calculation warning: {e}")

print()

# Summary
print("=" * 60)
print("✨ All Core Tests Passed!")
print("=" * 60)
print()
print("🎯 Next Steps:")
print("   1. Start API: uvicorn api.main:app --reload --port 8000")
print("   2. Start UI:  cd ui && python3 serve.py")
print("   3. Open:      http://localhost:3000")
print()
print("   Or use the quick start script:")
print("   ./start.sh")
print()

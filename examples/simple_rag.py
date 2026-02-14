"""
Simple RAG example using RAG Debugger.

This example demonstrates how to integrate RAG Debugger with a basic
LangChain RAG pipeline using FAISS vector store and OpenAI.

Requirements:
    - OpenAI API key set in environment (OPENAI_API_KEY)
    
Usage:
    python examples/simple_rag.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema import Document

from langchain import RagDebuggerCallback


def create_sample_documents():
    """Create sample documents about RAG."""
    docs = [
        Document(
            page_content="Retrieval Augmented Generation (RAG) is a technique that combines information retrieval with text generation. It retrieves relevant documents from a knowledge base and uses them as context for generating responses.",
            metadata={"source": "rag_intro.txt", "page": 1}
        ),
        Document(
            page_content="RAG systems typically consist of three main components: a retriever that finds relevant documents, a prompt template that formats the context, and a language model that generates the final response.",
            metadata={"source": "rag_architecture.txt", "page": 1}
        ),
        Document(
            page_content="The main advantage of RAG is that it grounds the language model's responses in retrieved facts, reducing hallucinations and improving accuracy. It also allows the system to access up-to-date information without retraining.",
            metadata={"source": "rag_benefits.txt", "page": 1}
        ),
        Document(
            page_content="Common retrieval methods in RAG include vector similarity search using embeddings, BM25 for keyword-based retrieval, and hybrid approaches that combine both.",
            metadata={"source": "retrieval_methods.txt", "page": 1}
        ),
        Document(
            page_content="RAG Debugger is a tool that helps developers understand and optimize their RAG pipelines by capturing retrieval events, prompt assembly, and LLM generation costs.",
            metadata={"source": "rag_debugger.txt", "page": 1}
        ),
    ]
    return docs


def main():
    """Run a simple RAG example with debugging."""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set!")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-key-here'")
        return
    
    print("🚀 RAG Debugger - Simple Example")
    print("=" * 50)
    
    # Create sample documents
    print("\n📄 Creating sample documents...")
    documents = create_sample_documents()
    print(f"   Created {len(documents)} documents")
    
    # Create embeddings and vector store
    print("\n🔢 Creating embeddings and vector store...")
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    print("   ✓ Vector store created")
    
    # Create retriever
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 3}  # Retrieve top 3 documents
    )
    
    # Create LLM
    print("\n🤖 Initializing LLM...")
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7
    )
    print("   ✓ LLM initialized")
    
    # Create RAG chain with debugger
    print("\n🔧 Setting up RAG chain with debugger...")
    query = "What is RAG and what are its main benefits?"
    
    # Create debugger callback
    callback = RagDebuggerCallback(query=query, auto_save=True)
    
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        callbacks=[callback],
        return_source_documents=True
    )
    print("   ✓ Chain configured")
    
    # Run the query
    print(f"\n❓ Query: {query}")
    print("\n⏳ Running RAG pipeline...")
    
    try:
        result = chain.invoke({"query": query})
        
        print("\n" + "=" * 50)
        print("📊 RESULTS")
        print("=" * 50)
        
        print(f"\n💬 Answer:")
        print(f"   {result['result']}")
        
        print(f"\n📄 Retrieved Documents: {len(result.get('source_documents', []))}")
        for i, doc in enumerate(result.get('source_documents', []), 1):
            print(f"   {i}. {doc.metadata.get('source', 'Unknown')} - {doc.page_content[:100]}...")
        
        # Get summary from debugger
        summary = callback.get_summary()
        print("\n" + "=" * 50)
        print("🐛 DEBUG SUMMARY")
        print("=" * 50)
        print(f"   Session ID: {summary['session_id']}")
        print(f"   Documents Retrieved: {summary['documents_retrieved']}")
        print(f"   Total Cost: ${summary.get('total_cost', 0):.5f}")
        print(f"   Total Duration: {summary.get('total_duration_ms', 0)}ms")
        
        print("\n✅ Session saved to database!")
        print(f"\nTo view this session:")
        print(f"   ragdebug trace {summary['session_id']}")
        print(f"   or")
        print(f"   ragdebug trace last")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("✨ Done! Check ~/.ragdebug/ragdebug.db for stored data")
    print("=" * 50)


if __name__ == "__main__":
    main()

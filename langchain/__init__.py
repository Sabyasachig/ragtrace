"""
LangChain integration for RAGTrace.
"""

from .middleware import RagTracer, SimpleRagTracer

# Backwards compatibility aliases
RagDebuggerCallback = RagTracer
SimpleRagDebugger = SimpleRagTracer

__all__ = ["RagTracer", "SimpleRagTracer", "RagDebuggerCallback", "SimpleRagDebugger"]

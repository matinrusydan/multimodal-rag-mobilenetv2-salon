"""Compatibility entrypoint for the canonical lightweight RAG runtime.

Research CV modules and models remain available offline, not in the web runtime.
"""
from app.rag_app import app

__all__ = ['app']

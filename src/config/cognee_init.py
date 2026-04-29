"""
Centralized Cognee initialization for the research graph system.

This module MUST be imported before any Cognee operations to ensure:
1. Environment variables are set correctly
2. cognee.setup() is called to create relational DB + default user
3. Embedding and vector engines are configured properly

Usage:
    from src.config.cognee_init import ensure_cognee_initialized
    ensure_cognee_initialized()
"""
import sys
sys.path.insert(0, '/home/cuizhixing/cognee-env/lib/python3.10/site-packages')

import os
import asyncio

# Set environment defaults BEFORE importing cognee
os.environ.setdefault("VECTOR_DB_PROVIDER", "lancedb")
os.environ.setdefault("EMBEDDING_PROVIDER", "fastembed")
os.environ.setdefault("EMBEDDING_MODEL", "jinaai/jina-embeddings-v3")
os.environ.setdefault("EMBEDDING_DIMENSIONS", "1024")
os.environ.setdefault("GRAPH_DATABASE_PROVIDER", "kuzu")
os.environ.setdefault("DB_PROVIDER", "sqlite")

import cognee
from cognee.modules.engine.operations.setup import setup as cognee_setup

_initialized = False


async def _setup_cognee():
    """Async setup: configure + initialize relational DB."""
    global _initialized
    if _initialized:
        return

    # Configure embedding
    cognee.config.set_embedding_provider("fastembed")
    cognee.config.set_embedding_model("jinaai/jina-embeddings-v3")
    cognee.config.set_embedding_dimensions(1024)

    # CRITICAL: Create relational DB tables and default user
    await cognee_setup()

    _initialized = True


def ensure_cognee_initialized():
    """
    Synchronous entry point. Must be called before any Cognee operations.
    Safe to call multiple times (idempotent).
    """
    global _initialized
    if _initialized:
        return

    try:
        loop = asyncio.get_running_loop()
        # If we're in an async context, create a task
        # But we need sync initialization, so use run_coroutine_threadsafe
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _setup_cognee())
            future.result(timeout=30)
    except RuntimeError:
        # No running loop - we can use asyncio.run
        asyncio.run(_setup_cognee())


async def ensure_cognee_initialized_async():
    """Async entry point. Call this if you're already in an async function."""
    await _setup_cognee()

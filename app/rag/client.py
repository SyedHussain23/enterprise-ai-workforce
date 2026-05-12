"""
ChromaDB singleton client.

Previously, `rag_tool.py` created `OpenAIEmbeddings()` and `Chroma()` on
EVERY request. Under any real load this causes:
  - Connection pool exhaustion on ChromaDB's SQLite backend
  - Repeated embedding model initialization overhead
  - No shared connection state

Pattern: module-level singleton initialized once at startup. FastAPI's
startup lifecycle hook calls `init_rag_client()`. All RAG calls share
the same client instance.
"""
import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db")

MAX_RETRIEVAL_CHUNKS = 5   # how many raw docs to retrieve before filtering
MAX_FINAL_CHUNKS = 2       # how many to include in context after filtering


@lru_cache(maxsize=1)
def _get_embeddings() -> OpenAIEmbeddings:
    """Created once, reused forever. lru_cache(1) ensures singleton semantics."""
    return OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)


@lru_cache(maxsize=1)
def get_chroma_client() -> Chroma:
    """
    Singleton Chroma client.
    lru_cache(1) guarantees one instance per process lifetime.
    In production with multiple workers, each worker process gets its own
    instance — that's correct and expected for ChromaDB.
    """
    return Chroma(
        persist_directory=VECTOR_DB_PATH,
        embedding_function=_get_embeddings(),
    )

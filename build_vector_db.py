"""
Rebuild the ChromaDB vector store from all documents in data/.

Run this once after initial setup, or any time you add/remove .txt files
directly from the filesystem (bypassing the admin upload API).

Usage:
    python build_vector_db.py
"""
from app.rag.vector_store import create_vector_store
from app.rag.hybrid_retriever import invalidate_bm25_cache

print("Building vector database from data/ knowledge base...")

create_vector_store()
invalidate_bm25_cache()

print("✅ Vector database built and BM25 index invalidated successfully.")
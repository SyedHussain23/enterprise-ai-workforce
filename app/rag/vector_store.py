from langchain_chroma import Chroma

from app.core.logger import get_logger
from app.rag.client import VECTOR_DB_PATH, _get_embeddings, get_chroma_client
from app.rag.document_loader import load_documents

logger = get_logger(__name__)


def create_vector_store() -> Chroma:
    """Build ChromaDB from scratch. Run once during initial setup."""
    docs = load_documents()
    if not docs:
        raise ValueError("No documents loaded — check data/ directory")

    store = Chroma.from_documents(
        documents=docs,
        embedding=_get_embeddings(),
        persist_directory=VECTOR_DB_PATH,
    )
    logger.info("vector_store.created", path=VECTOR_DB_PATH, docs=len(docs))
    return store


def get_vector_store() -> Chroma:
    """Return the singleton client. Prefer get_chroma_client() for RAG queries."""
    return get_chroma_client()
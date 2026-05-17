from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.logger import get_logger
from app.rag.client import get_chroma_client
from app.rag.hybrid_retriever import invalidate_bm25_cache

logger = get_logger(__name__)

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def process_uploaded_document(file_path: str) -> str:
    """Add a text document to the ChromaDB knowledge base."""
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    chunks = _SPLITTER.split_documents(documents)

    client = get_chroma_client()
    client.add_documents(chunks)
    invalidate_bm25_cache()

    logger.info("document_processor.added", file=file_path, chunks=len(chunks))
    return f"Document indexed: {file_path} ({len(chunks)} chunks)"

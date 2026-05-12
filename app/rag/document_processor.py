from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter

from app.rag.client import get_chroma_client


def process_uploaded_document(file_path: str) -> str:
    """Add a document to the ChromaDB knowledge base."""
    loader = TextLoader(file_path)
    documents = loader.load()

    chunks = CharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(documents)

    client = get_chroma_client()
    client.add_documents(chunks)

    return f"Document successfully added to knowledge base: {file_path}"
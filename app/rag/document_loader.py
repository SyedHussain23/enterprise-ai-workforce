# app/rag/document_loader.py
from __future__ import annotations

import os

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.logger import get_logger

logger = get_logger(__name__)

# Folders inside data/ that we index
_SUPPORTED_CATEGORIES = {"HR", "IT", "Finance", "Company"}

# Larger chunks → more context per retrieval; overlap preserves boundary sentences
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def load_documents():
    """
    Walk data/<category>/*.txt for all supported categories.
    Returns a list of LangChain Document chunks with source + category metadata.
    """
    base_path = "data"

    if not os.path.exists(base_path):
        logger.error("document_loader.missing_data_folder", path=base_path)
        return []

    raw_docs = []

    for category in os.listdir(base_path):
        if category not in _SUPPORTED_CATEGORIES:
            continue

        category_path = os.path.join(base_path, category)
        if not os.path.isdir(category_path):
            continue

        txt_files = [f for f in os.listdir(category_path) if f.endswith(".txt")]

        for filename in sorted(txt_files):
            file_path = os.path.join(category_path, filename)
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                docs   = loader.load()
                for doc in docs:
                    doc.metadata["source"]   = filename
                    doc.metadata["category"] = category
                raw_docs.extend(docs)
            except Exception as exc:
                logger.warning(
                    "document_loader.file_skipped",
                    file=file_path,
                    error=str(exc),
                )

    if not raw_docs:
        logger.warning("document_loader.no_documents_found", base=base_path)
        return []

    chunks = _SPLITTER.split_documents(raw_docs)

    logger.info(
        "document_loader.loaded",
        raw_docs=len(raw_docs),
        chunks=len(chunks),
        categories=list(_SUPPORTED_CATEGORIES),
    )
    return chunks

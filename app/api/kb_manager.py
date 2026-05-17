# app/api/kb_manager.py
from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.dependencies import require_admin
from app.core.logger import get_logger
from app.rag.hybrid_retriever import invalidate_bm25_cache
from app.rag.vector_store import create_vector_store

logger = get_logger(__name__)

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

_DATA_ROOT = Path("data").resolve()
_ALLOWED_CATEGORIES = {"HR", "IT", "Finance", "Company"}
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _safe_path(category: str, filename: str | None = None) -> Path:
    """Resolve path and reject any traversal attempt."""
    if category not in _ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Allowed: {sorted(_ALLOWED_CATEGORIES)}",
        )

    folder = (_DATA_ROOT / category).resolve()

    if filename is None:
        return folder

    # Reject names with path separators or double-dots
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    resolved = (folder / safe_name).resolve()
    if not str(resolved).startswith(str(folder)):
        raise HTTPException(status_code=400, detail="Path traversal detected.")

    return resolved


# ── List Documents ────────────────────────────────────────────────────────────
@router.get("/documents", dependencies=[Depends(require_admin)])
def list_documents():
    """Return all documents in the knowledge base, grouped by category."""
    result: dict[str, list[str]] = {}

    for cat in _ALLOWED_CATEGORIES:
        folder = _DATA_ROOT / cat
        if folder.is_dir():
            result[cat] = sorted(
                f for f in os.listdir(folder) if f.endswith(".txt")
            )

    return result


# ── Upload Document ───────────────────────────────────────────────────────────
@router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_document(
    category: str,
    file: UploadFile = File(...),
):
    """Upload a .txt document into the specified category and rebuild the vector DB."""
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted.")

    dest_path = _safe_path(category, file.filename)

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {_MAX_FILE_SIZE // 1024 // 1024} MB.",
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(content)

    logger.info("kb_manager.uploaded", category=category, filename=file.filename)

    create_vector_store()
    invalidate_bm25_cache()

    return {"message": "Uploaded and indexed successfully", "path": str(dest_path.relative_to(_DATA_ROOT))}


# ── Delete Document ───────────────────────────────────────────────────────────
@router.delete("/delete", dependencies=[Depends(require_admin)])
def delete_document(category: str, filename: str):
    """Delete a document from the knowledge base and rebuild the vector DB."""
    file_path = _safe_path(category, filename)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    file_path.unlink()
    logger.info("kb_manager.deleted", category=category, filename=filename)

    create_vector_store()
    invalidate_bm25_cache()

    return {"message": f"{filename} deleted and index updated."}


# ── Rebuild Index ─────────────────────────────────────────────────────────────
@router.post("/rebuild", dependencies=[Depends(require_admin)])
def rebuild_kb():
    """Force a full rebuild of the ChromaDB vector store."""
    create_vector_store()
    invalidate_bm25_cache()
    logger.info("kb_manager.rebuilt")
    return {"message": "Vector DB rebuilt successfully."}

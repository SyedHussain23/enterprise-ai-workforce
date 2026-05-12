from fastapi import APIRouter, UploadFile, File
import os
import shutil

from app.rag.vector_store import create_vector_store

router = APIRouter()

DATA_PATH = "data"


# -----------------------------
# 📄 List Documents
# -----------------------------
@router.get("/kb/documents")
def list_documents():

    all_docs = {}

    if not os.path.exists(DATA_PATH):
        return {}

    for folder in os.listdir(DATA_PATH):

        folder_path = os.path.join(DATA_PATH, folder)

        if os.path.isdir(folder_path):
            all_docs[folder] = os.listdir(folder_path)

    return all_docs


# -----------------------------
# 📤 Upload Document
# -----------------------------
@router.post("/kb/upload")
async def upload_document(
    category: str,
    file: UploadFile = File(...)
):

    folder_path = os.path.join(DATA_PATH, category)

    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 🔥 Rebuild vector DB
    create_vector_store()

    return {"message": "Uploaded & Indexed Successfully"}


# -----------------------------
# ❌ Delete Document
# -----------------------------
@router.delete("/kb/delete")
def delete_document(category: str, filename: str):

    file_path = os.path.join(DATA_PATH, category, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    # 🔥 Rebuild vector DB
    create_vector_store()

    return {"message": "Deleted & Updated DB"}


# -----------------------------
# 🔁 Rebuild Entire DB
# -----------------------------
@router.post("/kb/rebuild")
def rebuild_kb():

    create_vector_store()

    return {"message": "Vector DB Rebuilt"}
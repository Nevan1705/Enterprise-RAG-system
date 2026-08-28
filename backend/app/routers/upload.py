"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/routers/upload.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : REST API Router for document ingestion. Validates file types,
              computes SHA256 fingerprints to eliminate duplicate ingestion,
              persists temporary uploads, and queues background Celery tasks.
================================================================================
"""
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.logger import setup_logger
from app.services.hashing import sha256_bytes
from app.services.vector_store import is_hash_indexed
from app.models.schemas import UploadResponse, UploadResult
from app.workers.tasks import process_document

# Initialize router and logger
router = APIRouter()
logger = setup_logger(__name__)

# Supported file extensions
ALLOWED = {".pdf", ".docx", ".doc"}


# -----------------------------------------------------------------------------
# POST /upload/ — Multi-file Ingestion Endpoint
# -----------------------------------------------------------------------------
@router.post(
    "/",
    response_model=UploadResponse,
    summary="Upload one or more PDF/DOCX files for asynchronous ingestion",
    description=(
        "Upload multiple documents for background processing.\n\n"
        "Each file is:\n"
        "1. Validated for supported format (PDF/DOCX).\n"
        "2. Fingerprinted with a SHA256 checksum.\n"
        "3. Checked for duplicate presence in the index.\n"
        "4. Saved temporarily and dispatched to a background Celery worker.\n\n"
        "Returns task receipts with task IDs for real-time progress polling."
    ),
)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Handles multi-file uploads, performs validation, and queues background processing.
    """
    if not files:
        raise HTTPException(400, "No files provided in upload payload")

    results: list[UploadResult] = []

    for uf in files:
        name = uf.filename or "unknown"
        ext  = Path(name).suffix.lower()

        # 1. Extension validation
        if ext not in ALLOWED:
            raise HTTPException(400, f"Unsupported extension '{ext}'. Allowed: {ALLOWED}")

        # 2. Compute SHA256 hash for deduplication
        raw = await uf.read()
        file_hash = sha256_bytes(raw)
        doc_id    = file_hash

        logger.info(f"[UPLOAD] Processing file='{name}', computed doc_id='{doc_id}'")

        # 3. Check if file is already indexed
        if is_hash_indexed(file_hash):
            logger.info(f"[UPLOAD] Duplicate detected: '{name}' already indexed in vector store")
            results.append(UploadResult(
                doc_id=doc_id, 
                source=name,
                status="duplicate", 
                duplicated=True,
            ))
            continue

        # 4. Save to temporary upload location
        temp_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{name}")
        with open(temp_path, "wb") as f:
            f.write(raw)

        # 5. Dispatch async background task to Celery
        task = process_document.delay(temp_path, name, doc_id, file_hash)
        logger.info(f"[UPLOAD] Dispatched Celery task_id='{task.id}' for file='{name}'")

        results.append(UploadResult(
            doc_id=doc_id, 
            source=name,
            status="queued", 
            duplicated=False,
            task_id=task.id,
        ))

    return UploadResponse(uploads=results)

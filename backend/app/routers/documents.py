"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/routers/documents.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : REST API Router for document catalog and index lifecycle management.
              Provides document listing and deletion endpoints with atomic
              FAISS index rebuilds upon document removal.
================================================================================
"""
from fastapi import APIRouter, HTTPException

from app.core.logger import setup_logger
from app.services.vector_store import (
    get_all_documents,
    get_indexed_doc_ids,
    is_doc_indexed,
    delete_document,
)
from app.models.schemas import DocumentsResponse, DeleteResponse

# Initialize router and logger
router = APIRouter()
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# GET /upload/documents — List Indexed Documents
# -----------------------------------------------------------------------------
@router.get(
    "/documents",
    response_model=DocumentsResponse,
    summary="List all indexed documents",
    description="Returns deduplicated indexed document metadata with IDs and source filenames.",
)
async def list_documents():
    """
    Returns an inventory of all currently indexed documents in the vector store.
    """
    return DocumentsResponse(
        documents=get_all_documents(),
        indexed_doc_ids=get_indexed_doc_ids(),
    )


# -----------------------------------------------------------------------------
# DELETE /upload/document/{doc_id} — Delete Document & Rebuild Index
# -----------------------------------------------------------------------------
@router.delete(
    "/document/{doc_id}",
    response_model=DeleteResponse,
    summary="Delete a document and rebuild FAISS index",
    description=(
        "Removes ALL chunks for `doc_id` from the FAISS index.\n\n"
        "**Atomic Rebuilding**: Since FAISS lacks native deletion, the vector index "
        "is filtered and rebuilt from remaining memory state atomically.\n\n"
        "Also purges tracking sets to allow re-uploading if needed."
    ),
)
def delete_document_endpoint(doc_id: str):
    """
    Deletes the specified document and triggers an atomic index rebuild.
    """
    logger.info(f"[DELETE REQUEST] Initiated deletion for doc_id='{doc_id}'")

    if not is_doc_indexed(doc_id):
        raise HTTPException(404, f"Document with ID '{doc_id}' not found in vector store")

    success = delete_document(doc_id)
    if not success:
        raise HTTPException(500, f"Deletion and rebuild failed for doc_id='{doc_id}'")

    logger.info(f"[DELETE SUCCESS] Completed deletion and rebuild for doc_id='{doc_id}'")
    return DeleteResponse(
        success=True,
        deleted_doc_id=doc_id,
        message=(
            f"Document {doc_id[:16]}... and all associated chunks were purged. "
            "FAISS index has been rebuilt successfully."
        ),
    )

"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/workers/tasks.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Background Celery Tasks for asynchronous document ingestion.
              Executes a 5-stage ingestion pipeline emitting real-time percentage
              progress updates to Redis:
                - 10% : Document text extraction (pypdf / python-docx)
                - 30% : Recursive semantic text chunking
                - 50% : Embedding vector generation (SentenceTransformers)
                - 80% : Indexing embeddings into persistent FAISS vector store
                - 100%: Pipeline completion & temporary file cleanup
================================================================================
"""
import os

import app.core.ssl_patch  # noqa: F401 - Apply SSL fix for model downloads on Windows
from app.workers.celery_app import celery_app
from app.core.logger import setup_logger
from app.services.document_loader import extract_text
from app.services.chunking import chunk_text
from app.services.vector_store import embed_texts, add_documents

# Initialize module logger
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# Celery Asynchronous Ingestion Task: process_document
# -----------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    name="app.workers.tasks.process_document",
    max_retries=3,
    default_retry_delay=5,
)
def process_document(
    self,
    file_path: str,
    filename: str,
    doc_id: str,
    file_hash: str,
) -> dict:
    """
    Executes end-to-end background ingestion for a single document.
    
    Args:
        self: Bound Celery Task instance (used for update_state).
        file_path (str): Local filesystem path of uploaded temporary file.
        filename (str): Original document name.
        doc_id (str): Unique SHA256 document identifier.
        file_hash (str): File content checksum.
        
    Returns:
        dict: Ingestion summary result metadata.
    """
    logger.info(f"[TASK START] Ingestion task started for doc_id='{doc_id}', file='{filename}'")

    try:
        # -- Step 1: Text Extraction (10% Progress) --
        self.update_state(
            state="STARTED",
            meta={"progress": 10, "step": "Extracting text from document"},
        )
        raw_text = extract_text(file_path, filename)
        if not raw_text.strip():
            raise ValueError(f"No extractable text found in file: {filename}")
        logger.info(f"[TASK] Extracted {len(raw_text)} characters from {filename}")

        # -- Step 2: Recursive Semantic Chunking (30% Progress) --
        self.update_state(
            state="STARTED",
            meta={"progress": 30, "step": "Chunking document text"},
        )
        documents = chunk_text(raw_text, doc_id, file_hash, filename)
        logger.info(f"[TASK] Created {len(documents)} chunks from {filename}")

        # -- Step 3: Vector Embeddings Generation (50% Progress) --
        self.update_state(
            state="STARTED",
            meta={"progress": 50, "step": "Generating SentenceTransformer embeddings"},
        )
        embeddings = embed_texts([d.page_content for d in documents])
        logger.info(f"[TASK] Embeddings generated successfully with shape={embeddings.shape}")

        # -- Step 4: FAISS Vector Indexing (80% Progress) --
        self.update_state(
            state="STARTED",
            meta={"progress": 80, "step": "Indexing chunks into FAISS vector store"},
        )
        add_documents(embeddings, documents, doc_id, file_hash, filename)
        logger.info(f"[TASK] Successfully indexed {len(documents)} chunks for doc_id='{doc_id}'")

        # -- Step 5: Temporary File Cleanup --
        try:
            os.remove(file_path)
        except Exception:
            pass

        # Final Success Payload (100% Progress)
        result = {
            "doc_id": doc_id,
            "source": filename,
            "chunks_indexed": len(documents),
            "status": "completed",
            "progress": 100,
            "step": "Complete",
        }
        logger.info(f"[TASK DONE] Ingestion complete for doc_id='{doc_id}' ({len(documents)} chunks)")
        return result

    except Exception as exc:
        logger.error(f"[TASK ERROR] Ingestion failed for doc_id='{doc_id}': {exc}")
        raise self.retry(exc=exc)

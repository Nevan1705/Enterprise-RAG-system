"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/vector_store.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : High-Performance FAISS Vector Store Engine. Features:
              - SentenceTransformers all-MiniLM-L6-v2 (384-dimensional embeddings)
              - L2 normalization converting Inner Product into Cosine Similarity
              - Persistent index storage (index.faiss + index.pkl state)
              - Atomic index rebuilds upon document deletion (handling FAISS limitation)
              - Cross-process synchronization and thread-safe RLock protection
================================================================================
"""
import os
import pickle
import threading
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logger import setup_logger

# Initialize module logger and reentrant thread synchronization lock
logger = setup_logger(__name__)
_lock = threading.RLock()
_model: Optional[SentenceTransformer] = None

# -----------------------------------------------------------------------------
# In-Memory State & Cache Tracking
# -----------------------------------------------------------------------------
_doc_ids_indexed: set[str] = set()
_file_hashes_indexed: set[str] = set()
_doc_sources_by_id: dict[str, str] = {}
# Master store: list of (embedding_vector np.ndarray shape(384,), LangChain Document)
_documents_store: list[tuple[np.ndarray, Document]] = []
_last_mtime: float = 0.0


# -----------------------------------------------------------------------------
# 1. Embedding Model Management & Inference
# -----------------------------------------------------------------------------
def _get_model() -> SentenceTransformer:
    """
    Lazy-loads and returns the SentenceTransformer embedding model singleton.
    """
    global _model
    if _model is None:
        logger.info(f"[EMBED] Loading SentenceTransformer: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Generates L2-normalized 384-dimensional embedding vectors for a batch of texts.
    
    Args:
        texts (list[str]): List of input text strings to embed.
        
    Returns:
        np.ndarray: float32 matrix of shape (N, 384) with unit norm vectors.
    """
    m = _get_model()
    vecs = m.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    # L2-normalization for exact cosine similarity via inner product
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return (vecs / norms).astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    """
    Generates an L2-normalized embedding vector for a single query string.
    """
    return embed_texts([text])


# -----------------------------------------------------------------------------
# 2. Persistence & State Synchronization
# -----------------------------------------------------------------------------
def _load_state() -> None:
    """
    Deserializes indexed documents, hashes, and vectors from disk pickle file.
    """
    global _doc_ids_indexed, _file_hashes_indexed, _doc_sources_by_id, _documents_store, _last_mtime
    pkl = settings.FAISS_PKL_PATH
    if not os.path.exists(pkl):
        return
    try:
        with open(pkl, "rb") as f:
            state = pickle.load(f)
        _last_mtime = os.path.getmtime(pkl)
        _doc_ids_indexed     = state.get("doc_ids", set())
        _file_hashes_indexed = state.get("file_hashes", set())
        _doc_sources_by_id   = state.get("doc_sources", {})
        _documents_store     = state.get("documents_store", [])
        logger.info(
            f"[STORE] Loaded state: {len(_doc_ids_indexed)} docs, "
            f"{len(_documents_store)} chunks from disk"
        )
    except Exception as e:
        logger.error(f"[STORE] Load state failed: {e}")


def _save_state() -> None:
    """
    Atomically serializes current vector store memory state to disk.
    Writes first to a temporary file, then performs atomic replace.
    """
    global _last_mtime
    pkl = settings.FAISS_PKL_PATH
    tmp = pkl + ".tmp"
    state = {
        "doc_ids": _doc_ids_indexed,
        "file_hashes": _file_hashes_indexed,
        "doc_sources": _doc_sources_by_id,
        "documents_store": _documents_store,
    }
    with open(tmp, "wb") as f:
        pickle.dump(state, f)
    os.replace(tmp, pkl)
    try:
        _last_mtime = os.path.getmtime(pkl)
    except Exception:
        pass
    logger.debug("[STORE] State atomically persisted to disk")


def _rebuild_faiss() -> None:
    """
    Rebuilds the FAISS IndexFlatIP index directly from _documents_store.
    Called on document additions and deletions.
    """
    faiss_path = settings.FAISS_INDEX_PATH
    if not _documents_store:
        if os.path.exists(faiss_path):
            os.remove(faiss_path)
        logger.info("[STORE] FAISS index cleared (empty store)")
        return
        
    dim = _documents_store[0][0].shape[0]
    index = faiss.IndexFlatIP(dim)
    vecs = np.stack([v for v, _ in _documents_store], axis=0).astype(np.float32)
    index.add(vecs)
    faiss.write_index(index, faiss_path)
    logger.info(f"[STORE] FAISS rebuilt successfully: {index.ntotal} vectors (dim={dim})")


# Load initial state upon module import
_load_state()


def _check_sync() -> None:
    """
    Checks if external processes (e.g. Celery workers) have updated the state file
    and synchronizes in-memory structures if modifications are detected.
    """
    with _lock:
        pkl = settings.FAISS_PKL_PATH
        if os.path.exists(pkl):
            try:
                mtime = os.path.getmtime(pkl)
                if mtime > _last_mtime:
                    _load_state()
            except Exception as e:
                logger.error(f"[STORE] Synchronization check failed: {e}")


# -----------------------------------------------------------------------------
# 3. Public Vector Store Operations
# -----------------------------------------------------------------------------
def is_hash_indexed(h: str) -> bool:
    """Checks if a document with the specified SHA256 hash is already indexed."""
    _check_sync()
    with _lock:
        return h in _file_hashes_indexed


def is_doc_indexed(doc_id: str) -> bool:
    """Checks if a document with the specified doc_id is currently present."""
    _check_sync()
    with _lock:
        return doc_id in _doc_ids_indexed


def get_all_documents() -> list[dict]:
    """Returns deduplicated summary of all indexed documents."""
    _check_sync()
    with _lock:
        seen: set[str] = set()
        out: list[dict] = []
        for _, doc in _documents_store:
            did = doc.metadata.get("doc_id")
            if did and did not in seen:
                seen.add(did)
                out.append({"doc_id": did, "source": doc.metadata.get("source", "?")})
        return out


def get_indexed_doc_ids() -> list[str]:
    """Returns a list of all indexed document IDs."""
    _check_sync()
    with _lock:
        return list(_doc_ids_indexed)


def get_total_chunks() -> int:
    """Returns the total number of vector chunks stored in the index."""
    with _lock:
        return len(_documents_store)


def add_documents(
    embeddings: np.ndarray,
    documents: list[Document],
    doc_id: str,
    file_hash: str,
    source: str,
) -> None:
    """
    Appends newly generated chunk embeddings and documents to the store,
    triggers FAISS index rebuild, and persists state.
    """
    _check_sync()
    with _lock:
        for i, doc in enumerate(documents):
            _documents_store.append((embeddings[i], doc))
        _doc_ids_indexed.add(doc_id)
        _file_hashes_indexed.add(file_hash)
        _doc_sources_by_id[doc_id] = source
        _rebuild_faiss()
        _save_state()
        logger.info(f"[STORE] Added {len(documents)} chunks for doc_id={doc_id}")


def delete_document(doc_id: str) -> bool:
    """
    Removes ALL chunks associated with doc_id and performs an atomic rebuild
    of the FAISS index from the remaining documents in memory.
    
    Returns:
        bool: True if document existed and was deleted, False otherwise.
    """
    global _documents_store, _doc_ids_indexed, _file_hashes_indexed, _doc_sources_by_id

    with _lock:
        if doc_id not in _doc_ids_indexed:
            logger.warning(f"[DELETE] Target doc_id='{doc_id}' not found in index")
            return False

        before = len(_documents_store)
        # Filter out chunks matching target doc_id
        _documents_store = [
            (v, d) for v, d in _documents_store
            if d.metadata.get("doc_id") != doc_id
        ]
        removed = before - len(_documents_store)

        _doc_ids_indexed.discard(doc_id)
        _doc_sources_by_id.pop(doc_id, None)

        # Recompute remaining valid file hashes
        _file_hashes_indexed = {
            d.metadata["file_hash"]
            for _, d in _documents_store
            if d.metadata.get("file_hash")
        }

        _rebuild_faiss()   # Mandatory full rebuild after deletion
        _save_state()

        logger.info(
            f"[DELETE] Removed {removed} chunks for doc_id={doc_id}. "
            f"Store now contains {len(_documents_store)} total chunks."
        )
        return True


def similarity_search(
    query_vec: np.ndarray,
    k: int = 5,
    doc_id_filter: Optional[str] = None,
    similarity_threshold: Optional[float] = None,
) -> list[Document]:
    """
    Executes an inner product (cosine) similarity search against the FAISS index.
    Supports document filtering and score thresholding.
    
    Args:
        query_vec (np.ndarray): L2-normalized query embedding vector.
        k (int): Maximum number of matching chunks to return.
        doc_id_filter (Optional[str]): Optional doc_id to restrict search scope.
        similarity_threshold (Optional[float]): Minimum cosine similarity score.
        
    Returns:
        list[Document]: Ordered list of top-K matching LangChain Document chunks.
    """
    _check_sync()
    with _lock:
        if not _documents_store:
            return []
        faiss_path = settings.FAISS_INDEX_PATH
        if not os.path.exists(faiss_path):
            return []

        index = faiss.read_index(faiss_path)
        qv = query_vec.astype(np.float32).reshape(1, -1)

        # Filtered Search Execution
        if doc_id_filter:
            fetch_k = k * 10
            D, idxs = index.search(qv, min(fetch_k, index.ntotal))
            results: list[Document] = []
            for j, i in enumerate(idxs[0]):
                if i < 0 or i >= len(_documents_store):
                    continue
                score = D[0][j]
                if similarity_threshold is not None and score < similarity_threshold:
                    continue
                _, doc = _documents_store[i]
                if doc.metadata.get("doc_id") == doc_id_filter:
                    results.append(doc)
                    if len(results) >= k:
                        break
        # Unfiltered Global Search Execution
        else:
            D, idxs = index.search(qv, min(k, index.ntotal))
            results = []
            for j, i in enumerate(idxs[0]):
                if i < 0 or i >= len(_documents_store):
                    continue
                score = D[0][j]
                if similarity_threshold is not None and score < similarity_threshold:
                    continue
                results.append(_documents_store[i][1])

        return results

"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/retriever.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Semantic retrieval orchestrator. Converts natural language queries
              into embedding vectors, executes similarity search against FAISS,
              applies optional document isolation, and formats standardized
              context blocks for LLM prompt augmentation.
================================================================================
"""
from typing import Optional
from langchain_core.documents import Document

from app.services.vector_store import embed_query, similarity_search
from app.core.config import settings
from app.core.logger import setup_logger

# Initialize module logger
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# Semantic Retrieval & Context Prompt Assembly
# -----------------------------------------------------------------------------
def retrieve_and_build_context(
    question: str,
    k: Optional[int] = None,
    doc_id_filter: Optional[str] = None,
    isolate_top_doc: bool = False,
    similarity_threshold: Optional[float] = None,
) -> tuple[list[Document], str]:
    """
    Performs end-to-end retrieval and builds an augmented context block.
    
    Args:
        question (str): User's natural language question.
        k (Optional[int]): Number of chunks to retrieve (defaults to settings.TOP_K).
        doc_id_filter (Optional[str]): Restricts retrieval to a single document ID.
        isolate_top_doc (bool): If True and no filter provided, restricts chunks to the single best-matching doc.
        similarity_threshold (Optional[float]): Minimum cosine similarity threshold score.
        
    Returns:
        tuple[list[Document], str]: (Matching chunk documents, Formatted context string).
    """
    # 1. Embed query and execute vector search
    k = k or settings.TOP_K
    qvec = embed_query(question)
    docs = similarity_search(
        qvec, 
        k=k, 
        doc_id_filter=doc_id_filter, 
        similarity_threshold=similarity_threshold
    )

    # 2. Return empty context if no matching chunks found
    if not docs:
        logger.info(f"[RETRIEVER] No matching documents found for query='{question[:60]}'")
        return [], ""

    # 3. Document isolation: isolate context to highest scoring document if requested
    if isolate_top_doc and not doc_id_filter:
        top_doc_id = docs[0].metadata.get("doc_id")
        docs = [d for d in docs if d.metadata.get("doc_id") == top_doc_id]

    # 4. Synthesize structured context string with source headers
    parts = []
    for chunk_idx, doc in enumerate(docs):
        src = doc.metadata.get("source", "unknown")
        did = doc.metadata.get("doc_id", "unknown")
        parts.append(f"[Chunk {chunk_idx + 1} | source={src} | doc_id={did}]\n{doc.page_content}")

    context = "\n\n".join(parts)
    logger.info(f"[RETRIEVER] Context built: {len(docs)} chunks, {len(context)} characters")
    return docs, context

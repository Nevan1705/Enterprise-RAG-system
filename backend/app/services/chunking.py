"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/chunking.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Semantic text splitting and chunking service. Utilizes LangChain's
              RecursiveCharacterTextSplitter with configurable character limits
              and sliding window overlaps to maintain contextual boundaries.
================================================================================
"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logger import setup_logger

# Initialize module logger
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# Recursive Text Splitting & Metadata Enrichment
# -----------------------------------------------------------------------------
def chunk_text(
    raw_text: str,
    doc_id: str,
    file_hash: str,
    source: str,
) -> list[Document]:
    """
    Splits raw extracted text into LangChain Document objects with granular metadata.
    
    Args:
        raw_text (str): Complete text extracted from source document.
        doc_id (str): Unique document identifier (SHA256 digest).
        file_hash (str): Raw file content hash for deduplication tracking.
        source (str): Original human-readable filename.
        
    Returns:
        list[Document]: List of LangChain Document objects containing chunk content and metadata.
    """
    # Initialize recursive text splitter with hierarchy of semantic separators
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    # Generate chunk strings
    text_chunks = splitter.split_text(raw_text)
    logger.info(f"[CHUNKING] Generated {len(text_chunks)} chunks for source='{source}'")

    # Wrap each text chunk in a Document model with contextual metadata
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": source,
                "doc_id": doc_id,
                "file_hash": file_hash,
                "chunk_id": chunk_idx,
            },
        )
        for chunk_idx, chunk in enumerate(text_chunks)
    ]
    
    return documents

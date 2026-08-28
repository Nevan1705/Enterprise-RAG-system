"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/document_loader.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Multi-format document parser. Handles raw text extraction from PDF
              and Microsoft Word (DOCX) files using pypdf and python-docx.
              Includes robust error handling and length telemetry.
================================================================================
"""
from pathlib import Path
from app.core.logger import setup_logger

# Initialize module logger
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# Main Text Extraction Dispatcher
# -----------------------------------------------------------------------------
def extract_text(file_path: str, filename: str) -> str:
    """
    Extracts plain text content from supported file formats.
    
    Args:
        file_path (str): Local filesystem path to the uploaded document.
        filename (str): Original filename used to inspect file extension.
        
    Returns:
        str: Concatenated text content extracted from the document.
        
    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = Path(filename).suffix.lower()
    
    # PDF Dispatcher
    if ext == ".pdf":
        return _load_pdf(file_path)
        
    # Word Document Dispatcher (.docx, .doc)
    if ext in (".docx", ".doc"):
        return _load_docx(file_path)
        
    raise ValueError(f"Unsupported file type: {ext}")


# -----------------------------------------------------------------------------
# PDF Document Extraction Implementation
# -----------------------------------------------------------------------------
def _load_pdf(path: str) -> str:
    """
    Iterates through all pages of a PDF document using pypdf and extracts text.
    """
    from pypdf import PdfReader
    
    reader = PdfReader(path)
    text_chunks = []
    
    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            text_chunks.append(page_text)
            
    extracted_text = "\n".join(text_chunks)
    logger.info(f"[LOADER] PDF extracted {len(extracted_text)} chars ({len(reader.pages)} pages) <- {path}")
    return extracted_text


# -----------------------------------------------------------------------------
# Microsoft Word Document Extraction Implementation
# -----------------------------------------------------------------------------
def _load_docx(path: str) -> str:
    """
    Parses all paragraph nodes of a DOCX document using python-docx.
    """
    from docx import Document
    
    doc = Document(path)
    extracted_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    logger.info(f"[LOADER] DOCX extracted {len(extracted_text)} chars <- {path}")
    return extracted_text

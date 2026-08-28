"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/hashing.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Cryptographic hashing utilities for document fingerprinting and
              O(1) deduplication across concurrent upload workflows.
================================================================================
"""
import hashlib


# -----------------------------------------------------------------------------
# SHA256 Fingerprint Computation
# -----------------------------------------------------------------------------
def sha256_bytes(data: bytes) -> str:
    """
    Computes a cryptographic SHA256 hexadecimal digest from raw binary bytes.
    Used for tamper-proof document identification and duplicate detection.
    
    Args:
        data (bytes): Raw file byte stream.
        
    Returns:
        str: 64-character lowercase hexadecimal hash digest.
    """
    return hashlib.sha256(data).hexdigest()

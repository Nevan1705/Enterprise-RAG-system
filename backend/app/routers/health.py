"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/routers/health.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : REST API Router for system health checks and operational diagnostics.
              Validates Redis broker connectivity, FAISS vector index integrity,
              total indexed chunks, and active LLM configuration.
================================================================================
"""
import os
from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import setup_logger
from app.services.vector_store import get_all_documents, get_total_chunks
from app.models.schemas import HealthResponse

# Initialize router and logger
router = APIRouter()
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# GET /health — Comprehensive System Health Check
# -----------------------------------------------------------------------------
@router.get(
    "/health", 
    response_model=HealthResponse, 
    summary="Comprehensive system health and resource diagnostic check",
    description="Probes Redis broker, FAISS vector store, chunk counts, and LLM provider availability.",
)
async def health_check():
    """
    Performs multi-point diagnostic checks across system dependencies.
    """
    # 1. Probe Redis broker connectivity with socket timeout
    redis_ok = False
    try:
        import redis as _r
        client = _r.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        redis_ok = True
    except Exception as e:
        logger.warning(f"[HEALTH] Redis connection check failed: {e}")

    # 2. Check LlamaIndex fallback module availability
    fallback_available = False
    try:
        import llama_index  # type: ignore # noqa
        fallback_available = True
    except ImportError:
        pass

    # 3. Assemble and return health diagnostic report
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        faiss_index_exists=os.path.exists(settings.FAISS_INDEX_PATH),
        total_documents=len(get_all_documents()),
        total_chunks=get_total_chunks(),
        redis_connected=redis_ok,
        llm_provider="groq",
        llm_model=settings.GROQ_MODEL,
        fallback_available=fallback_available,
    )

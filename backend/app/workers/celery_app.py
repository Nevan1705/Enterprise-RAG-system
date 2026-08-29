"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/workers/celery_app.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Distributed Task Queue Worker Configuration (Celery + Redis).
              Configures task serialization, worker concurrency settings,
              retry intervals, late acknowledgements, and extended result tracking.
================================================================================
"""
import app.core.ssl_patch  # noqa: F401 - Apply SSL fix for worker model downloads
from celery import Celery
from app.core.config import settings

# -----------------------------------------------------------------------------
# Celery Application Instance Initialization
# -----------------------------------------------------------------------------
celery_app = Celery(
    "rag_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

# -----------------------------------------------------------------------------
# Celery Worker Configuration & Optimization
# -----------------------------------------------------------------------------
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,          # Track STARTED state for real-time progress
    task_acks_late=True,              # Ensure task is acknowledged only upon completion
    worker_prefetch_multiplier=1,     # Fair task dispatching
    task_max_retries=3,               # Automatic retries on failure
    task_default_retry_delay=5,       # Retry backoff interval in seconds
    result_extended=True,             # Store custom task metadata and progress dicts
)

"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/routers/status.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : REST API Router for background task monitoring. Inspects Celery
              task states (PENDING, STARTED, SUCCESS, FAILURE), extracts progress
              percentages and step messages from custom task metadata.
================================================================================
"""
from fastapi import APIRouter
from app.models.schemas import TaskStatusResponse
from app.core.logger import setup_logger

# Initialize router and logger
router = APIRouter()
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# GET /upload/status/{task_id} — Task Polling Endpoint
# -----------------------------------------------------------------------------
@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Poll status and real-time progress of an ingestion task",
    description="Retrieves live execution status, completion percentage (0-100%), and active pipeline step.",
)
async def get_task_status(task_id: str):
    """
    Queries Celery AsyncResult backend for status and metadata of task_id.
    """
    from celery.result import AsyncResult
    from app.workers.celery_app import celery_app

    res = AsyncResult(task_id, app=celery_app)
    status = res.status

    resp = TaskStatusResponse(task_id=task_id, status=status)

    # Extract real-time step and progress % from Celery state metadata
    if status == "STARTED":
        meta = res.info or {}
        resp.progress = meta.get("progress")
        resp.step = meta.get("step")
    elif status == "SUCCESS":
        r = res.result or {}
        resp.result   = r
        resp.progress = r.get("progress", 100)
        resp.step     = r.get("step", "Complete")
    elif status == "FAILURE":
        resp.error = str(res.result)

    return resp

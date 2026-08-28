"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/models/schemas.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Pydantic Data Transfer Objects (DTOs) and Domain Models. Defines
              strict request/response validation schemas for file upload, task polling,
              semantic querying, chat session history, health checks, and QA test cases.
================================================================================
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# 1. Document Upload & Ingestion Schemas
# -----------------------------------------------------------------------------
class UploadResult(BaseModel):
    """Represents the individual outcome of a single uploaded document."""
    doc_id: str = Field(..., description="Unique SHA256 document identifier")
    source: str = Field(..., description="Original filename of the document")
    status: str = Field(..., description="Ingestion status: queued, duplicate, error")
    duplicated: bool = Field(..., description="Flag indicating if file was already indexed")
    task_id: Optional[str] = Field(None, description="Celery background task ID if queued")


class UploadResponse(BaseModel):
    """Response payload containing array of upload results."""
    uploads: list[UploadResult]


class DocumentInfo(BaseModel):
    """Metadata summary of an indexed document."""
    doc_id: str
    source: str


class DocumentsResponse(BaseModel):
    """Response payload listing all indexed documents and IDs in the vector store."""
    documents: list[DocumentInfo]
    indexed_doc_ids: list[str]


class TaskStatusResponse(BaseModel):
    """Real-time task tracking progress payload for Celery background jobs."""
    task_id: str
    status: str = Field(..., description="STARTED, SUCCESS, FAILURE, PENDING")
    result: Optional[dict] = Field(None, description="Result payload on successful completion")
    error: Optional[str] = Field(None, description="Error message if task failed")
    progress: Optional[int] = Field(None, description="Percentage of completion (0-100%)")
    step: Optional[str] = Field(None, description="Human-readable current ingestion step")


class DeleteResponse(BaseModel):
    """Response payload confirming document deletion and FAISS index rebuild."""
    success: bool
    deleted_doc_id: str
    message: str


# -----------------------------------------------------------------------------
# 2. Semantic Query & QA Engine Schemas
# -----------------------------------------------------------------------------
class QueryRequest(BaseModel):
    """Request payload for semantic querying or testcase generation."""
    question: str = Field(..., min_length=3, description="Natural language question or QA prompt")
    doc_id: Optional[str] = Field(
        None,
        description="Optional filter to isolate retrieval to a specific document.",
    )
    k: Optional[int] = Field(
        None,
        description="Number of chunks to retrieve (defaults to settings.TOP_K).",
    )
    session_id: Optional[str] = Field(None, description="Session ID for chat history persistence")


class QueryResponse(BaseModel):
    """Response payload from semantic retrieval and LLM synthesis."""
    question: str
    answer: str
    sources: list[str]
    doc_ids_used: list[str]
    chunks_used: int
    provider: str = Field("groq", description="LLM provider: groq, llamaindex, or none")
    session_id: Optional[str] = None
    mode: str = Field("chat", description="'chat' for regular Q&A or 'testcases' for QA automation")
    download_url: Optional[str] = Field(None, description="Direct URL to download generated Excel file")
    total_testcases: Optional[int] = Field(None, description="Total count of validated test cases")


# -----------------------------------------------------------------------------
# 3. Chat Session Management Schemas
# -----------------------------------------------------------------------------
class ChatMessage(BaseModel):
    """Individual conversation message entry with source citations."""
    role: str = Field(..., description="Message author: user or assistant")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    sources: Optional[list[str]] = None
    doc_ids: Optional[list[str]] = None
    chunks_used: Optional[int] = None
    provider: Optional[str] = None


class ChatSession(BaseModel):
    """Complete conversation history model for a session."""
    session_id: str
    created_at: str
    messages: list[ChatMessage]


# -----------------------------------------------------------------------------
# 4. System Health & Observability Schemas
# -----------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """System diagnostic status payload reporting resource health."""
    status: str = Field(..., description="'healthy' or 'degraded'")
    faiss_index_exists: bool
    total_documents: int
    total_chunks: int
    redis_connected: bool
    llm_provider: str
    llm_model: Optional[str] = None
    fallback_available: bool


# -----------------------------------------------------------------------------
# 5. Quality Assurance (QA) Test Case Model
# -----------------------------------------------------------------------------
class TestCaseItem(BaseModel):
    """Structured QA Test Case Schema matching enterprise testing standards."""
    test_case_id: str = Field(..., description="Unique Test Case Identifier (e.g., TC_001)")
    requirement_id: str = Field(..., description="Associated Business Requirement ID (e.g., REQ_001)")
    test_scenario: str = Field(..., description="High-level scenario or feature under test")
    test_case_description: str = Field(..., description="Detailed objective and description of the test")
    preconditions: str = Field(..., description="System preconditions and initial state")
    test_steps: list[str] = Field(..., description="Ordered array of execution steps")
    test_data: str = Field(..., description="Input parameters and testing data required")
    expected_result: str = Field(..., description="Expected system behavior and acceptance criteria")

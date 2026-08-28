"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/routers/query.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : REST API Router for semantic search, QA generation, and chat history.
              Orchestrates vector retrieval, context isolation, test case synthesis,
              styled Excel exports, session persistence, and transcript downloads.
================================================================================
"""
import os
import uuid
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse

from app.core.logger import setup_logger
from app.services.retriever import retrieve_and_build_context
from app.services.llm import LLMService
from app.services import chat_store
from app.services.testcase_service import is_testcase_request, generate_testcases_json
from app.services.excel_export import export_testcases_to_excel, DOWNLOADS_DIR
from app.models.schemas import QueryRequest, QueryResponse, ChatSession

# Initialize router and logger
router = APIRouter()
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# 1. POST /query/ — Semantic Query & QA Engine Endpoint
# -----------------------------------------------------------------------------
@router.post(
    "/",
    response_model=QueryResponse,
    summary="Query the Enterprise RAG System",
    description=(
        "Submit natural language questions or QA testcase generation instructions.\n"
        "Retrieves relevant document chunks from FAISS, constructs grounded context, "
        "and queries the resilient LLM engine (Groq primary with LlamaIndex failover).\n"
        "Automatically persists message history into active chat session."
    ),
)
def query_documents(request: QueryRequest):
    """
    Executes semantic retrieval, context synthesis, test case generation, or standard Q&A.
    """
    question    = request.question.strip()
    k           = request.k or None
    is_testcase = is_testcase_request(question)
    
    # Ensure sufficient context chunks for test case generation
    if is_testcase:
        k = max(k or 0, 5)
        
    doc_filter = request.doc_id or None
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        f"[QUERY] session_id={session_id} query='{question[:80]}' "
        f"doc_filter={doc_filter} k={k}"
    )

    # Initialize chat session and record user query
    chat_store.get_or_create(session_id)
    chat_store.append(session_id, "user", question)

    # 1. Semantic Retrieval: Retrieve relevant chunks and format context
    docs, context = retrieve_and_build_context(
        question, 
        k=k, 
        doc_id_filter=doc_filter, 
        isolate_top_doc=is_testcase, 
        similarity_threshold=0.35 if is_testcase else None
    )

    # Handle case where no relevant chunks exist in index
    if not docs:
        answer = "Not found in provided documents"
        chat_store.append(
            session_id, "assistant", answer,
            sources=[], doc_ids=[], chunks_used=0, provider="none",
        )
        return QueryResponse(
            question=question, 
            answer=answer,
            sources=[], 
            doc_ids_used=[], 
            chunks_used=0,
            provider="none", 
            session_id=session_id,
        )

    # 2. Branch: QA Test Case Generation Workflow
    if is_testcase:
        try:
            logger.info(f"[QUERY] Generating multi-batch test cases for session={session_id}")
            testcases, provider = generate_testcases_json(context, question)
            filename = export_testcases_to_excel(testcases)
            
            total = len(testcases)
            download_url = f"/query/downloads/{filename}"
            answer = f"Generated {total} testcases successfully."
            
            chat_store.append(
                session_id, "assistant", answer,
                sources=list({d.metadata.get("source", "?") for d in docs}),
                doc_ids=list({d.metadata.get("doc_id", "?") for d in docs}),
                chunks_used=len(docs),
                provider=provider,
            )
            
            return QueryResponse(
                question=question,
                answer=answer,
                sources=list({d.metadata.get("source", "?") for d in docs}),
                doc_ids_used=list({d.metadata.get("doc_id", "?") for d in docs}),
                chunks_used=len(docs),
                provider=provider,
                session_id=session_id,
                mode="testcases",
                download_url=download_url,
                total_testcases=total
            )
        except Exception as e:
            logger.error(f"[QUERY] Testcase generation failed: {e}")
            raise HTTPException(500, detail=f"Failed to generate testcases: {str(e)}")

    # 3. Branch: Standard Semantic Q&A Workflow via LLMService
    try:
        result = LLMService.generate(context, question)
    except RuntimeError as e:
        logger.error(f"[QUERY] LLM generation failed: {e}")
        raise HTTPException(500, detail=str(e))

    if "not found in provided documents" in result.answer.lower():
        sources = []
        doc_ids_used = []
        chunks_used = 0
    else:
        sources = list({d.metadata.get("source", "?") for d in docs})
        doc_ids_used = list({d.metadata.get("doc_id", "?") for d in docs})
        chunks_used = len(docs)

    # Persist assistant response in conversation memory
    chat_store.append(
        session_id, "assistant", result.answer,
        sources=sources,
        doc_ids=doc_ids_used,
        chunks_used=chunks_used,
        provider=result.provider,
    )

    logger.info(
        f"[QUERY DONE] provider={result.provider} retries={result.retries} "
        f"fallback={result.fallback_triggered} latency={result.latency_ms:.0f}ms"
    )

    return QueryResponse(
        question=question,
        answer=result.answer,
        sources=sources,
        doc_ids_used=doc_ids_used,
        chunks_used=chunks_used,
        provider=result.provider,
        session_id=session_id,
    )


# -----------------------------------------------------------------------------
# 2. GET /query/history/{session_id} — Retrieve Chat History
# -----------------------------------------------------------------------------
@router.get(
    "/history/{session_id}",
    response_model=ChatSession,
    summary="Retrieve chat history for a session",
)
async def get_history(session_id: str):
    """
    Returns complete conversation message history for session_id.
    """
    s = chat_store.get(session_id)
    if not s:
        raise HTTPException(404, f"Session '{session_id}' not found")
    return ChatSession(**s)


# -----------------------------------------------------------------------------
# 3. GET /query/history/{session_id}/download — Export Chat Transcripts
# -----------------------------------------------------------------------------
@router.get(
    "/history/{session_id}/download",
    summary="Download chat history transcript (JSON or TXT)",
)
async def download_history(
    session_id: str,
    format: str = Query("json", description="'json' or 'txt'"),
):
    """
    Exports session transcripts as formatted plain-text or structured JSON.
    """
    if format == "txt":
        content = chat_store.export_txt(session_id)
        if not content:
            raise HTTPException(404, f"Session '{session_id}' not found")
        return PlainTextResponse(
            content=content,
            headers={"Content-Disposition": f'attachment; filename="session_{session_id[:8]}.txt"'},
        )
    else:
        content = chat_store.export_json(session_id)
        if not content:
            raise HTTPException(404, f"Session '{session_id}' not found")
        return JSONResponse(
            content=chat_store.get(session_id),
            headers={"Content-Disposition": f'attachment; filename="session_{session_id[:8]}.json"'},
        )


# -----------------------------------------------------------------------------
# 4. GET /query/downloads/{filename} — Download Generated Test Cases (.xlsx)
# -----------------------------------------------------------------------------
@router.get(
    "/downloads/{filename}",
    summary="Download generated testcases Excel file",
)
async def download_testcase_file(filename: str):
    """
    Transfers the generated Excel spreadsheet file to client.
    """
    file_path = os.path.join(DOWNLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested Excel file not found")
    return FileResponse(
        file_path, 
        filename=filename, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

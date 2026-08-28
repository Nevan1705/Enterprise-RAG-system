# ⬡ Enterprise RAG Intelligence Platform v3

Production-grade RAG system with GROQ primary LLM, LlamaIndex fallback,
FAISS rebuild-on-delete, real-time Celery task tracking, and a corporate Streamlit UI.

---

## What's New in v3

| Feature | Details |
|---|---|
| Strict modular structure | `app/{routers,services,core,models,workers}` |
| **LLM Service** (`services/llm.py`) | All LLM calls here only — GROQ + retry → LlamaIndex fallback |
| LlamaIndex as wrapper | Calls secondary model, used ONLY inside LLMService |
| Real-time task tracking | Auto-polls every 1.5s — no manual refresh |
| Progress steps | 10%→extract 30%→chunk 50%→embed 80%→index 100%→done |
| LLM provider badge | Chat shows `groq` or `llamaindex` per response |
| Observability LLM panel | Shows provider, fallback status, retries config |

---

## Project Structure

```
rag_v3/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── upload.py           POST /upload/
│   │   │   ├── status.py           GET  /upload/status/{task_id}
│   │   │   ├── documents.py        GET  /upload/documents  DELETE /upload/document/{doc_id}
│   │   │   ├── query.py            POST /query/  GET /query/history/{sid}  GET /query/history/{sid}/download
│   │   │   └── health.py           GET  /health
│   │   ├── services/
│   │   │   ├── hashing.py          SHA256 deduplication
│   │   │   ├── document_loader.py  PDF/DOCX text extraction
│   │   │   ├── chunking.py         RecursiveCharacterTextSplitter
│   │   │   ├── vector_store.py     FAISS + delete rebuild
│   │   │   ├── retriever.py        Embed → search → context builder
│   │   │   ├── llm.py              ⚡ ALL LLM calls — GROQ + LlamaIndex fallback
│   │   │   └── chat_store.py       JSON session persistence
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logger.py
│   │   ├── models/schemas.py
│   │   └── workers/
│   │       ├── celery_app.py
│   │       └── tasks.py            Step-progress Celery task
│   ├── data/uploads/
│   ├── data/vector_store/
│   ├── chat_store/
│   └── logs/
├── frontend/app.py                 Corporate Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

```bash
cd rag_v3

python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env → set GROQ_API_KEY
```

---

## Running (4 terminals from `rag_v3/`)

### Terminal 1 — Redis
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Terminal 2 — FastAPI
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API docs: http://localhost:8000/docs

### Terminal 3 — Celery Worker
```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2
```

### Terminal 4 — Streamlit UI
```bash
cd frontend
streamlit run app.py --server.port 8501
```
UI: http://localhost:8501

---

## LLM Fallback Logic

```
Query arrives
    ↓
Call GROQ (attempt 1)
    ↓ fail (timeout/rate-limit/5xx)
Call GROQ (attempt 2)
    ↓ fail
Trigger LlamaIndex fallback
    ↓ fail
Raise controlled error → HTTP 500
```

Only transient errors trigger fallback.
Valid "not found in context" answers are NOT fallback triggers.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload/` | Upload PDF/DOCX |
| GET | `/upload/status/{task_id}` | Poll task (with progress %) |
| GET | `/upload/documents` | List indexed documents |
| DELETE | `/upload/document/{doc_id}` | Delete + rebuild FAISS |
| POST | `/query/` | RAG query (GROQ→LlamaIndex) |
| GET | `/query/history/{session_id}` | Chat history |
| GET | `/query/history/{session_id}/download?format=json\|txt` | Export |
| GET | `/health` | System health + LLM status |

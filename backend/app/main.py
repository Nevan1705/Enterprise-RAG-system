"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/main.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Central FastAPI application entry point. Configures lifespan event
              handlers, CORS middleware, and mounts modular REST API routers
              for document upload, background task tracking, document inventory,
              semantic retrieval queries, and health observability.
================================================================================
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.ssl_patch  # noqa: F401 - Apply SSL fix for model downloads on Windows
from app.core.logger import setup_logger
from app.routers import upload, query, status, documents, health

# Initialize module-level structured logger
logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# Application Lifespan Event Management
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle events.
    Initializes system resources on boot and performs graceful teardown on exit.
    """
    logger.info("=== Enterprise RAG System v3 Starting Up ===")
    yield
    logger.info("=== Enterprise RAG System v3 Shutting Down Gracefully ===")


# -----------------------------------------------------------------------------
# FastAPI Application Initialization
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Enterprise RAG Backend API",
    description="High-Performance Retrieval-Augmented Generation & QA Automation Platform v3",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# -----------------------------------------------------------------------------
# Cross-Origin Resource Sharing (CORS) Configuration
# -----------------------------------------------------------------------------
# Enables full cross-origin resource sharing to support Streamlit UI and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Router Registrations
# -----------------------------------------------------------------------------
# Upload & Document Ingestion Router Group
app.include_router(upload.router,    prefix="/upload",  tags=["Upload & Ingestion"])
app.include_router(status.router,    prefix="/upload",  tags=["Task Monitoring"])
app.include_router(documents.router, prefix="/upload",  tags=["Document Management"])

# Semantic Query & QA Engine Router Group
app.include_router(query.router,     prefix="/query",   tags=["Semantic Query & QA"])

# System Health & Observability Router Group
app.include_router(health.router,                       tags=["System Observability"])

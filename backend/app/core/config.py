"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/core/config.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Central application settings and environment configuration module.
              Loads parameters from .env files, defines default model paths,
              vector store directories, Redis broker URLs, and LLM hyperparameters.
================================================================================
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings  # type: ignore

# Resolve project root directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


# -----------------------------------------------------------------------------
# Enterprise Settings Configuration Model
# -----------------------------------------------------------------------------
class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables or .env file.
    Provides typed configurations for LLMs, Vector Store, Queues, and Chunking.
    """
    # -- Primary LLM Engine Settings (Groq Cloud LPU) --
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_RETRIES: int = 2
    LLM_TIMEOUT: int = 30

    # -- Secondary LLM Fallback Engine Settings (LlamaIndex) --
    LLAMAINDEX_MODEL: str = "openai/gpt-oss-120b"       # Routed through Groq / OpenAI compatible API
    LLAMAINDEX_API_KEY: str = ""                        # Falls back to GROQ_API_KEY if unspecified

    # -- Distributed Asynchronous Task Queue (Redis Broker) --
    REDIS_URL: str = "redis://localhost:6379/0"

    # -- Filesystem Directory Paths --
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")
    VECTOR_STORE_DIR: str = str(BASE_DIR / "data" / "vector_store")
    FAISS_INDEX_PATH: str = str(BASE_DIR / "data" / "vector_store" / "index.faiss")
    FAISS_PKL_PATH: str = str(BASE_DIR / "data" / "vector_store" / "index.pkl")
    CHAT_STORE_PATH: str = str(BASE_DIR / "chat_store" / "sessions.json")

    # -- Embedding Model Hyperparameters --
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # -- Document Splitting & Chunking Hyperparameters --
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    # -- Semantic Retrieval Hyperparameters --
    TOP_K: int = 5

    class Config:
        """Pydantic configuration options for environment file resolution."""
        env_file = str(BASE_DIR.parent / ".env")
        extra = "ignore"


# -----------------------------------------------------------------------------
# Global Settings Instance & Directory Initialization
# -----------------------------------------------------------------------------
# Instantiate singleton configuration
settings = Settings()

# Ensure all critical runtime directories exist on startup
for directory_path in [
    settings.UPLOAD_DIR,
    settings.VECTOR_STORE_DIR,
    str(Path(settings.CHAT_STORE_PATH).parent),
]:
    os.makedirs(directory_path, exist_ok=True)

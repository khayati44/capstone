import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import init_db
from backend.auth.router import router as auth_router
from backend.routers.upload import router as upload_router
from backend.routers.analyze import router as analyze_router
from backend.routers.query import router as query_router
from backend.routers.deductions import router as deductions_router
from backend.routers.guardrails import router as guardrails_router
from backend.routers.debug import router as debug_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    init_db()
    # Ingest knowledge base into ChromaDB if not already done
    try:
        from backend.rag.ingestion import ingest_knowledge_base
        ingest_knowledge_base()
    except Exception as e:
        print(f"[WARN] RAG ingestion skipped: {e}")
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title="Smart Tax Deduction Finder",
    description="AI-powered Indian tax deduction analyzer for salaried employees",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(analyze_router, prefix="/api", tags=["Analysis"])
app.include_router(query_router, prefix="/api", tags=["Query"])
app.include_router(deductions_router, prefix="/api", tags=["Deductions"])
app.include_router(guardrails_router, prefix="/api", tags=["Guardrails"])
app.include_router(debug_router, prefix="/api", tags=["Debug"])


@app.get("/health", tags=["Health"])
def health_check():
    return JSONResponse({"status": "ok", "version": "1.0.0"})

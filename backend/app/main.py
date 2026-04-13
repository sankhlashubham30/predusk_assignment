from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.base import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist yet (Alembic handles migrations in prod)
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Async Document Processing Workflow System",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers (imported here to avoid circular imports) ───────────────────────
from app.api.v1 import auth, documents, jobs, progress  # noqa: E402

app.include_router(auth.router, prefix=settings.API_V1_PREFIX + "/auth", tags=["Auth"])
app.include_router(documents.router, prefix=settings.API_V1_PREFIX + "/documents", tags=["Documents"])
app.include_router(jobs.router, prefix=settings.API_V1_PREFIX + "/jobs", tags=["Jobs"])
app.include_router(progress.router, prefix=settings.API_V1_PREFIX + "/progress", tags=["Progress"])


@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
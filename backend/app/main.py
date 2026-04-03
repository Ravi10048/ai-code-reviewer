from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.database import init_db
from app.exceptions import AppError
from app.routers import webhook, reviews, analytics, settings as settings_router
from app.utils.logger import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    setup_logging()
    logger = get_logger("app")
    logger.info("starting_up", port=settings.port, llm_provider=settings.llm_provider.value)

    # Initialize database
    init_db()
    logger.info("database_initialized")

    yield

    logger.info("shutting_down")


app = FastAPI(
    title="AI Code Reviewer",
    description="AI-powered code review bot for GitHub PRs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(webhook.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )


@app.get("/")
def root():
    return {
        "name": "AI Code Reviewer",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}

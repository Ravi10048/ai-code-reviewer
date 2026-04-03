from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.db.database import get_db
from app.db import repository as repo_db
from app.llm.factory import get_llm_provider, reset_provider

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingsResponse(BaseModel):
    llm_provider: str
    groq_model: str
    ollama_model: str
    ollama_base_url: str
    min_inline_severity: str
    max_files_per_review: int
    max_diff_lines_per_file: int


class SettingsUpdateRequest(BaseModel):
    llm_provider: str | None = None
    groq_model: str | None = None
    ollama_model: str | None = None
    min_inline_severity: str | None = None
    max_files_per_review: int | None = None
    max_diff_lines_per_file: int | None = None


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get current application settings."""
    # Merge env defaults with DB overrides
    db_settings = repo_db.get_all_settings(db)

    return SettingsResponse(
        llm_provider=db_settings.get("llm_provider", app_settings.llm_provider.value),
        groq_model=db_settings.get("groq_model", app_settings.groq_model),
        ollama_model=db_settings.get("ollama_model", app_settings.ollama_model),
        ollama_base_url=app_settings.ollama_base_url,
        min_inline_severity=db_settings.get(
            "min_inline_severity", app_settings.min_inline_severity.value
        ),
        max_files_per_review=int(
            db_settings.get("max_files_per_review", app_settings.max_files_per_review)
        ),
        max_diff_lines_per_file=int(
            db_settings.get(
                "max_diff_lines_per_file", app_settings.max_diff_lines_per_file
            )
        ),
    )


@router.put("", response_model=SettingsResponse)
def update_settings(
    request: SettingsUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update application settings."""
    updates = request.model_dump(exclude_none=True)

    for key, value in updates.items():
        repo_db.set_setting(db, key, str(value))

    # Reset LLM provider if changed
    if "llm_provider" in updates or "groq_model" in updates or "ollama_model" in updates:
        reset_provider()

    return get_settings(db)


@router.get("/health")
async def health_check():
    """Check the health of the LLM provider."""
    try:
        provider = get_llm_provider()
        is_healthy = await provider.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "provider": provider.provider_name,
            "model": provider.model_name,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

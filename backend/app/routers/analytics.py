from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import repository as repo_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary")
def get_analytics_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get aggregated analytics for the dashboard."""
    return repo_db.get_analytics_summary(db, days=days)


@router.get("/repos")
def get_repos(db: Session = Depends(get_db)):
    """List all connected repositories."""
    repos = repo_db.get_all_repos(db)
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "owner": r.owner,
            "name": r.name,
            "is_active": r.is_active,
            "installed_at": r.installed_at.isoformat() if r.installed_at else "",
        }
        for r in repos
    ]

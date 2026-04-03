from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db import repository as repo_db

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


class ReviewResponse(BaseModel):
    id: int
    repo_name: str
    pr_number: int
    pr_title: str
    pr_author: str
    pr_url: str
    total_issues: int
    critical_count: int
    warning_count: int
    suggestion_count: int
    files_reviewed: int
    llm_provider: str
    model_used: str
    review_duration_ms: int
    status: str
    error_message: str | None
    created_at: str
    completed_at: str | None

    class Config:
        from_attributes = True


class IssueResponse(BaseModel):
    id: int
    file_path: str
    line_number: int | None
    end_line_number: int | None
    severity: str
    category: str
    title: str
    description: str
    suggestion: str
    code_snippet: str
    confidence: float
    posted_to_github: bool

    class Config:
        from_attributes = True


class ReviewDetailResponse(ReviewResponse):
    issues: list[IssueResponse]


class PaginatedReviewsResponse(BaseModel):
    reviews: list[ReviewResponse]
    total: int
    limit: int
    offset: int


@router.get("", response_model=PaginatedReviewsResponse)
def list_reviews(
    repo_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all reviews with pagination."""
    reviews, total = repo_db.get_reviews(db, repo_id=repo_id, limit=limit, offset=offset)

    return PaginatedReviewsResponse(
        reviews=[
            ReviewResponse(
                id=r.id,
                repo_name=r.repo.full_name if r.repo else "",
                pr_number=r.pr_number,
                pr_title=r.pr_title,
                pr_author=r.pr_author,
                pr_url=r.pr_url,
                total_issues=r.total_issues,
                critical_count=r.critical_count,
                warning_count=r.warning_count,
                suggestion_count=r.suggestion_count,
                files_reviewed=r.files_reviewed,
                llm_provider=r.llm_provider,
                model_used=r.model_used,
                review_duration_ms=r.review_duration_ms,
                status=r.status,
                error_message=r.error_message,
                created_at=r.created_at.isoformat() if r.created_at else "",
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
            )
            for r in reviews
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{review_id}", response_model=ReviewDetailResponse)
def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get a single review with all its issues."""
    review = repo_db.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewDetailResponse(
        id=review.id,
        repo_name=review.repo.full_name if review.repo else "",
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_author=review.pr_author,
        pr_url=review.pr_url,
        total_issues=review.total_issues,
        critical_count=review.critical_count,
        warning_count=review.warning_count,
        suggestion_count=review.suggestion_count,
        files_reviewed=review.files_reviewed,
        llm_provider=review.llm_provider,
        model_used=review.model_used,
        review_duration_ms=review.review_duration_ms,
        status=review.status,
        error_message=review.error_message,
        created_at=review.created_at.isoformat() if review.created_at else "",
        completed_at=review.completed_at.isoformat() if review.completed_at else None,
        issues=[
            IssueResponse(
                id=i.id,
                file_path=i.file_path,
                line_number=i.line_number,
                end_line_number=i.end_line_number,
                severity=i.severity,
                category=i.category,
                title=i.title,
                description=i.description,
                suggestion=i.suggestion,
                code_snippet=i.code_snippet,
                confidence=i.confidence,
                posted_to_github=i.posted_to_github,
            )
            for i in review.issues
        ],
    )

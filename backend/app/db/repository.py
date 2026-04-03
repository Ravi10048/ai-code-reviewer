from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Sequence

from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.db.models import Repo, Review, Issue, AppSettings


# ── Repo Operations ──


def get_or_create_repo(
    db: Session,
    github_repo_id: int,
    name: str,
    owner: str,
    full_name: str,
    installation_id: int,
) -> Repo:
    repo = db.query(Repo).filter(Repo.github_repo_id == github_repo_id).first()
    if repo:
        repo.installation_id = installation_id
        repo.is_active = True
        db.commit()
        return repo

    repo = Repo(
        github_repo_id=github_repo_id,
        name=name,
        owner=owner,
        full_name=full_name,
        installation_id=installation_id,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def get_repo_by_full_name(db: Session, full_name: str) -> Repo | None:
    return db.query(Repo).filter(Repo.full_name == full_name).first()


def get_all_repos(db: Session) -> Sequence[Repo]:
    return db.query(Repo).filter(Repo.is_active == True).order_by(desc(Repo.installed_at)).all()


# ── Review Operations ──


def create_review(
    db: Session,
    repo_id: int,
    pr_number: int,
    pr_title: str,
    pr_author: str,
    pr_url: str,
    head_sha: str,
) -> Review:
    review = Review(
        repo_id=repo_id,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_author=pr_author,
        pr_url=pr_url,
        head_sha=head_sha,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def update_review_status(
    db: Session,
    review_id: int,
    status: str,
    error_message: str | None = None,
    review_duration_ms: int = 0,
    llm_provider: str = "",
    model_used: str = "",
    total_tokens_used: int = 0,
    files_reviewed: int = 0,
) -> Review | None:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        return None

    review.status = status
    review.error_message = error_message
    review.review_duration_ms = review_duration_ms
    review.llm_provider = llm_provider
    review.model_used = model_used
    review.total_tokens_used = total_tokens_used
    review.files_reviewed = files_reviewed

    if status in ("completed", "failed"):
        review.completed_at = datetime.now(timezone.utc)

    # Recount issues
    if status == "completed":
        issues = db.query(Issue).filter(Issue.review_id == review_id).all()
        review.total_issues = len(issues)
        review.critical_count = sum(1 for i in issues if i.severity == "critical")
        review.warning_count = sum(1 for i in issues if i.severity == "warning")
        review.suggestion_count = sum(1 for i in issues if i.severity == "suggestion")

    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, review_id: int) -> Review | None:
    return (
        db.query(Review)
        .options(joinedload(Review.issues), joinedload(Review.repo))
        .filter(Review.id == review_id)
        .first()
    )


def get_reviews(
    db: Session,
    repo_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[Review], int]:
    query = db.query(Review).options(joinedload(Review.repo))
    if repo_id:
        query = query.filter(Review.repo_id == repo_id)

    total = query.count()
    reviews = query.order_by(desc(Review.created_at)).offset(offset).limit(limit).all()
    return reviews, total


# ── Issue Operations ──


def create_issues(db: Session, review_id: int, issues: list[dict]) -> list[Issue]:
    db_issues = []
    for issue_data in issues:
        issue = Issue(review_id=review_id, **issue_data)
        db.add(issue)
        db_issues.append(issue)
    db.commit()
    for issue in db_issues:
        db.refresh(issue)
    return db_issues


def mark_issue_posted(db: Session, issue_id: int) -> None:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if issue:
        issue.posted_to_github = True
        db.commit()


# ── Analytics ──


def get_analytics_summary(db: Session, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.created_at >= since, Review.status == "completed")
        .scalar()
    ) or 0

    total_issues = (
        db.query(func.count(Issue.id))
        .join(Review)
        .filter(Review.created_at >= since, Review.status == "completed")
        .scalar()
    ) or 0

    severity_breakdown = (
        db.query(Issue.severity, func.count(Issue.id))
        .join(Review)
        .filter(Review.created_at >= since, Review.status == "completed")
        .group_by(Issue.severity)
        .all()
    )

    category_breakdown = (
        db.query(Issue.category, func.count(Issue.id))
        .join(Review)
        .filter(Review.created_at >= since, Review.status == "completed")
        .group_by(Issue.category)
        .all()
    )

    avg_duration = (
        db.query(func.avg(Review.review_duration_ms))
        .filter(Review.created_at >= since, Review.status == "completed")
        .scalar()
    ) or 0

    avg_issues_per_review = round(total_issues / total_reviews, 1) if total_reviews else 0

    # Reviews per day for chart
    daily_reviews = (
        db.query(
            func.date(Review.created_at).label("date"),
            func.count(Review.id).label("count"),
        )
        .filter(Review.created_at >= since, Review.status == "completed")
        .group_by(func.date(Review.created_at))
        .order_by(func.date(Review.created_at))
        .all()
    )

    # Top repos by review count
    top_repos = (
        db.query(Repo.full_name, func.count(Review.id).label("count"))
        .join(Review)
        .filter(Review.created_at >= since, Review.status == "completed")
        .group_by(Repo.full_name)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    return {
        "total_reviews": total_reviews,
        "total_issues": total_issues,
        "avg_issues_per_review": avg_issues_per_review,
        "avg_review_duration_ms": round(avg_duration),
        "severity_breakdown": {s: c for s, c in severity_breakdown},
        "category_breakdown": {c: n for c, n in category_breakdown},
        "daily_reviews": [{"date": str(d), "count": c} for d, c in daily_reviews],
        "top_repos": [{"repo": r, "count": c} for r, c in top_repos],
    }


# ── Settings ──


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = AppSettings(key=key, value=value)
        db.add(setting)
    db.commit()


def get_all_settings(db: Session) -> dict[str, str]:
    settings = db.query(AppSettings).all()
    return {s.key: s.value for s in settings}

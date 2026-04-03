from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Repo(Base):
    """GitHub repository connected to the app."""

    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_repo_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    installation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    reviews: Mapped[list["Review"]] = relationship(back_populates="repo", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Repo {self.full_name}>"


class Review(Base):
    """A single PR code review."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id"), index=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[str] = mapped_column(String(512), nullable=False)
    pr_author: Mapped[str] = mapped_column(String(255), nullable=False)
    pr_url: Mapped[str] = mapped_column(String(1024), default="")
    head_sha: Mapped[str] = mapped_column(String(40), nullable=False)

    # Review results
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    suggestion_count: Mapped[int] = mapped_column(Integer, default=0)
    files_reviewed: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    llm_provider: Mapped[str] = mapped_column(String(50), default="")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    review_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(
        Enum("pending", "in_progress", "completed", "failed", name="review_status"),
        default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    repo: Mapped["Repo"] = relationship(back_populates="reviews")
    issues: Mapped[list["Issue"]] = relationship(back_populates="review", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Review PR#{self.pr_number} status={self.status}>"


class Issue(Base):
    """A single issue found during code review."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), index=True)

    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    severity: Mapped[str] = mapped_column(
        Enum("critical", "warning", "suggestion", name="issue_severity"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        Enum("bug", "security", "performance", "style", "error_handling", name="issue_category"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, default="")
    code_snippet: Mapped[str] = mapped_column(Text, default="")

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    posted_to_github: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    review: Mapped["Review"] = relationship(back_populates="issues")

    def __repr__(self) -> str:
        return f"<Issue [{self.severity}] {self.file_path}:{self.line_number}>"


class AppSettings(Base):
    """Application-level settings stored in DB."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

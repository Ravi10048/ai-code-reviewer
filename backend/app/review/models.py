from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    """A single issue found during code review."""

    file_path: str
    line_number: int | None = None
    end_line_number: int | None = None
    severity: str = Field(description="critical, warning, or suggestion")
    category: str = Field(description="bug, security, performance, style, or error_handling")
    title: str = Field(description="Short one-line summary of the issue")
    description: str = Field(description="Detailed explanation of why this is a problem")
    suggestion: str = Field(default="", description="Suggested fix or improvement")
    code_snippet: str = Field(default="", description="The problematic code")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score 0-1")


class FileReviewResult(BaseModel):
    """Review result for a single file."""

    file_path: str
    issues: list[ReviewIssue] = []
    summary: str = ""


class FullReviewResult(BaseModel):
    """Complete review result for a PR."""

    summary: str
    overall_quality: str = Field(description="good, acceptable, needs_work, or critical")
    file_results: list[FileReviewResult] = []
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0
    suggestion_count: int = 0

    @property
    def all_issues(self) -> list[ReviewIssue]:
        issues = []
        for fr in self.file_results:
            issues.extend(fr.issues)
        return issues

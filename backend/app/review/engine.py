from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from app.config import settings, Severity
from app.exceptions import ReviewError
from app.github.diff_parser import FileDiff, filter_reviewable_files
from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm.factory import get_llm_provider
from app.review.models import FileReviewResult, FullReviewResult, ReviewIssue
from app.review.prompts import SYSTEM_PROMPT, get_file_review_prompt, get_summary_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReviewEngine:
    """Orchestrates the code review pipeline.

    Flow:
        1. Filter reviewable files from the diff
        2. Review each file individually via LLM
        3. Aggregate results
        4. Generate PR-level summary
    """

    def __init__(self, llm: BaseLLMProvider | None = None):
        self.llm = llm or get_llm_provider()
        self.total_tokens = 0

    async def review_pr(
        self,
        files: list[FileDiff],
        pr_title: str = "",
    ) -> FullReviewResult:
        """Run a full code review on a list of file diffs."""
        start_time = time.monotonic()

        # Filter to reviewable files
        reviewable = filter_reviewable_files(
            files, max_files=settings.max_files_per_review
        )

        if not reviewable:
            logger.info("no_reviewable_files")
            return FullReviewResult(
                summary="No code files to review in this PR.",
                overall_quality="good",
            )

        # Review each file
        file_results: list[FileReviewResult] = []
        for file_diff in reviewable:
            try:
                result = await self._review_file(file_diff)
                file_results.append(result)
            except Exception as e:
                logger.error(
                    "file_review_failed",
                    file=file_diff.file_path,
                    error=str(e),
                )
                file_results.append(
                    FileReviewResult(
                        file_path=file_diff.file_path,
                        summary=f"Review failed: {str(e)}",
                    )
                )

        # Count issues
        all_issues = []
        for fr in file_results:
            all_issues.extend(fr.issues)

        critical_count = sum(1 for i in all_issues if i.severity == "critical")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")
        suggestion_count = sum(1 for i in all_issues if i.severity == "suggestion")

        # Generate summary
        summary, quality = await self._generate_summary(
            pr_title=pr_title,
            file_results=file_results,
            total_issues=len(all_issues),
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)

        logger.info(
            "review_complete",
            files_reviewed=len(file_results),
            total_issues=len(all_issues),
            critical=critical_count,
            warnings=warning_count,
            suggestions=suggestion_count,
            duration_ms=duration_ms,
            total_tokens=self.total_tokens,
        )

        return FullReviewResult(
            summary=summary,
            overall_quality=quality,
            file_results=file_results,
            total_issues=len(all_issues),
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
        )

    async def _review_file(self, file_diff: FileDiff) -> FileReviewResult:
        """Review a single file diff."""
        diff_text = file_diff.raw_diff

        # Truncate very large diffs
        max_lines = settings.max_diff_lines_per_file
        diff_lines = diff_text.split("\n")
        if len(diff_lines) > max_lines:
            diff_text = "\n".join(diff_lines[:max_lines])
            diff_text += f"\n... (truncated, {len(diff_lines) - max_lines} lines omitted)"

        prompt = get_file_review_prompt(
            file_path=file_diff.file_path,
            language=file_diff.language,
            diff_content=diff_text,
        )

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        self.total_tokens += response.total_tokens

        # Parse LLM response
        data = self._parse_json_response(response.content)
        issues = []

        for issue_data in data.get("issues", []):
            try:
                issue = ReviewIssue(
                    file_path=file_diff.file_path,
                    line_number=issue_data.get("line_number"),
                    end_line_number=issue_data.get("end_line_number"),
                    severity=issue_data.get("severity", "suggestion"),
                    category=issue_data.get("category", "style"),
                    title=issue_data.get("title", "Untitled issue"),
                    description=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    code_snippet=issue_data.get("code_snippet", ""),
                    confidence=float(issue_data.get("confidence", 0.8)),
                )

                # Validate line number exists in the diff
                if issue.line_number:
                    valid_lines = file_diff.changed_line_numbers
                    if valid_lines and issue.line_number not in valid_lines:
                        # Find the nearest valid line
                        nearest = min(valid_lines, key=lambda x: abs(x - issue.line_number))
                        if abs(nearest - issue.line_number) <= 5:
                            issue.line_number = nearest
                        else:
                            # Line too far off — likely hallucinated, skip inline but keep issue
                            issue.line_number = None

                # Filter by confidence (drop low-confidence issues)
                if issue.confidence >= 0.7:
                    issues.append(issue)

            except Exception as e:
                logger.warning(
                    "issue_parse_failed",
                    file=file_diff.file_path,
                    error=str(e),
                    raw=issue_data,
                )

        return FileReviewResult(
            file_path=file_diff.file_path,
            issues=issues,
            summary=data.get("summary", ""),
        )

    async def _generate_summary(
        self,
        pr_title: str,
        file_results: list[FileReviewResult],
        total_issues: int,
        critical_count: int,
        warning_count: int,
        suggestion_count: int,
    ) -> tuple[str, str]:
        """Generate a PR-level review summary."""
        file_summaries = "\n".join(
            f"- `{fr.file_path}`: {fr.summary} ({len(fr.issues)} issues)"
            for fr in file_results
        )

        prompt = get_summary_prompt(
            pr_title=pr_title,
            files_changed=len(file_results),
            total_issues=total_issues,
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
            file_summaries=file_summaries,
        )

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt="You are a senior code reviewer writing a PR summary.",
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        self.total_tokens += response.total_tokens

        data = self._parse_json_response(response.content)
        summary = data.get("summary", "Review complete.")
        quality = data.get("overall_quality", "acceptable")

        if quality not in ("good", "acceptable", "needs_work", "critical"):
            quality = "acceptable"

        return summary, quality

    def _parse_json_response(self, content: str) -> dict:
        """Safely parse JSON from LLM response, handling markdown wrappers."""
        content = content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass

            logger.warning("json_parse_failed", content_preview=content[:200])
            return {"issues": [], "summary": "Failed to parse review response."}

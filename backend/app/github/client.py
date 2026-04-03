from __future__ import annotations

from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from app.config import settings, Severity
from app.github.auth import get_github_client
from app.github.diff_parser import FileDiff, parse_diff, filter_reviewable_files
from app.review.models import FullReviewResult, ReviewIssue
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Severity emoji map
SEVERITY_EMOJI = {
    "critical": "\U0001f6a8",  # 🚨
    "warning": "\u26a0\ufe0f",  # ⚠️
    "suggestion": "\U0001f4a1",  # 💡
}

CATEGORY_EMOJI = {
    "bug": "\U0001f41b",  # 🐛
    "security": "\U0001f512",  # 🔒
    "performance": "\u26a1",  # ⚡
    "style": "\U0001f3a8",  # 🎨
    "error_handling": "\U0001f6e1\ufe0f",  # 🛡️
}

QUALITY_EMOJI = {
    "good": "\u2705",  # ✅
    "acceptable": "\U0001f7e1",  # 🟡
    "needs_work": "\U0001f7e0",  # 🟠
    "critical": "\U0001f534",  # 🔴
}


class GitHubClient:
    """Handles all GitHub API interactions for PR reviews."""

    def __init__(self, installation_id: int):
        self.gh: Github = get_github_client(installation_id)
        self.installation_id = installation_id

    def get_pr(self, repo_full_name: str, pr_number: int) -> PullRequest:
        """Fetch a pull request object."""
        repo = self.gh.get_repo(repo_full_name)
        return repo.get_pull(pr_number)

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> list[FileDiff]:
        """Fetch and parse the PR diff into structured file diffs."""
        pr = self.get_pr(repo_full_name, pr_number)

        # Get diff via the PR files API for better structure
        files = pr.get_files()
        raw_patches: list[str] = []

        for f in files:
            if f.patch:
                # Reconstruct unified diff format
                header = f"diff --git a/{f.filename} b/{f.filename}\n"
                if f.status == "added":
                    header += "new file mode 100644\n"
                    header += "--- /dev/null\n"
                    header += f"+++ b/{f.filename}\n"
                elif f.status == "removed":
                    header += f"--- a/{f.filename}\n"
                    header += "+++ /dev/null\n"
                else:
                    header += f"--- a/{f.filename}\n"
                    header += f"+++ b/{f.filename}\n"
                raw_patches.append(header + f.patch)

        full_diff = "\n".join(raw_patches)
        parsed = parse_diff(full_diff)

        logger.info(
            "pr_diff_fetched",
            repo=repo_full_name,
            pr=pr_number,
            files=len(parsed),
        )
        return parsed

    def post_review_summary(
        self,
        repo_full_name: str,
        pr_number: int,
        review_result: FullReviewResult,
    ) -> None:
        """Post the review summary as a PR comment."""
        pr = self.get_pr(repo_full_name, pr_number)
        body = self._format_summary_comment(review_result)
        pr.create_issue_comment(body)

        logger.info(
            "summary_comment_posted",
            repo=repo_full_name,
            pr=pr_number,
        )

    def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        issues: list[ReviewIssue],
        head_sha: str,
        file_diffs: list[FileDiff],
    ) -> list[int]:
        """Post inline review comments on specific lines.

        Returns list of issue indices that were successfully posted.
        """
        pr = self.get_pr(repo_full_name, pr_number)
        min_severity = settings.min_inline_severity
        posted_indices = []

        # Build a lookup for diff hunks
        diff_lookup = {f.file_path: f for f in file_diffs}

        for idx, issue in enumerate(issues):
            # Only post inline for issues meeting severity threshold
            if Severity(issue.severity) < min_severity:
                continue

            # Must have a valid line number
            if not issue.line_number:
                continue

            # Verify the file exists in the diff
            file_diff = diff_lookup.get(issue.file_path)
            if not file_diff:
                continue

            # Get the hunk containing this line (needed for GitHub API)
            hunk = file_diff.get_hunk_for_line(issue.line_number)
            if not hunk:
                continue

            body = self._format_inline_comment(issue)

            try:
                pr.create_review_comment(
                    body=body,
                    commit=self.gh.get_repo(repo_full_name).get_commit(head_sha),
                    path=issue.file_path,
                    line=issue.line_number,
                )
                posted_indices.append(idx)
                logger.debug(
                    "inline_comment_posted",
                    file=issue.file_path,
                    line=issue.line_number,
                )
            except Exception as e:
                logger.warning(
                    "inline_comment_failed",
                    file=issue.file_path,
                    line=issue.line_number,
                    error=str(e),
                )

        logger.info(
            "inline_comments_posted",
            total_issues=len(issues),
            posted=len(posted_indices),
            repo=repo_full_name,
            pr=pr_number,
        )
        return posted_indices

    def _format_summary_comment(self, result: FullReviewResult) -> str:
        """Format the review summary as a GitHub markdown comment."""
        quality_emoji = QUALITY_EMOJI.get(result.overall_quality, "")

        lines = [
            f"## {quality_emoji} AI Code Review",
            "",
            result.summary,
            "",
        ]

        if result.total_issues > 0:
            lines.extend([
                "### Issues Found",
                "",
                f"| Severity | Count |",
                f"|----------|-------|",
                f"| \U0001f6a8 Critical | {result.critical_count} |",
                f"| \u26a0\ufe0f Warning | {result.warning_count} |",
                f"| \U0001f4a1 Suggestion | {result.suggestion_count} |",
                "",
            ])

            # List critical and warning issues in the summary
            important_issues = [
                i for i in result.all_issues
                if i.severity in ("critical", "warning")
            ]
            if important_issues:
                lines.append("### Key Issues")
                lines.append("")
                for issue in important_issues:
                    emoji = SEVERITY_EMOJI.get(issue.severity, "")
                    cat_emoji = CATEGORY_EMOJI.get(issue.category, "")
                    location = f"`{issue.file_path}"
                    if issue.line_number:
                        location += f":{issue.line_number}"
                    location += "`"
                    lines.append(
                        f"- {emoji} {cat_emoji} **{issue.title}** — {location}"
                    )
                    if issue.description:
                        lines.append(f"  {issue.description}")
                lines.append("")
        else:
            lines.extend([
                "\u2705 **No issues found!** The code looks clean.",
                "",
            ])

        # File summary
        if result.file_results:
            lines.extend([
                "<details>",
                "<summary>Files Reviewed</summary>",
                "",
            ])
            for fr in result.file_results:
                issue_count = len(fr.issues)
                status = "\u2705" if issue_count == 0 else f"\u26a0\ufe0f {issue_count} issues"
                lines.append(f"- `{fr.file_path}` — {status}")
            lines.extend(["", "</details>", ""])

        lines.extend([
            "---",
            "*Reviewed by [AI Code Reviewer](https://github.com/raviranjan/ai-code-reviewer) \u2022 "
            f"Powered by {result.file_results[0].issues[0].severity if result.all_issues else 'LLM'}*",
        ])

        # Fix: use the actual provider info
        lines[-1] = (
            "*Reviewed by [AI Code Reviewer](https://github.com/raviranjan/ai-code-reviewer)*"
        )

        return "\n".join(lines)

    def _format_inline_comment(self, issue: ReviewIssue) -> str:
        """Format a single inline review comment."""
        emoji = SEVERITY_EMOJI.get(issue.severity, "")
        cat_emoji = CATEGORY_EMOJI.get(issue.category, "")

        lines = [
            f"{emoji} **{issue.severity.upper()}** {cat_emoji} `{issue.category}`",
            "",
            f"**{issue.title}**",
            "",
            issue.description,
        ]

        if issue.suggestion:
            lines.extend([
                "",
                f"\U0001f527 **Suggestion:**",  # 🔧
                issue.suggestion,
            ])

        if issue.code_snippet:
            lines.extend([
                "",
                "```",
                issue.code_snippet,
                "```",
            ])

        lines.extend([
            "",
            f"*Confidence: {int(issue.confidence * 100)}%*",
        ])

        return "\n".join(lines)

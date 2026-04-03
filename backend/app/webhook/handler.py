from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.db.database import get_db_context
from app.db import repository as repo_db
from app.github.client import GitHubClient
from app.review.engine import ReviewEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thread pool for blocking GitHub API calls
_executor = ThreadPoolExecutor(max_workers=4)


async def handle_pull_request_event(payload: dict) -> dict:
    """Handle a pull_request webhook event.

    Triggers review on:
        - opened: New PR created
        - synchronize: New commits pushed to PR
        - reopened: PR was closed and reopened
    """
    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        logger.info("pr_event_skipped", action=action)
        return {"status": "skipped", "reason": f"Action '{action}' not reviewed"}

    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})
    installation = payload.get("installation", {})

    pr_number = pr_data.get("number")
    pr_title = pr_data.get("title", "")
    pr_author = pr_data.get("user", {}).get("login", "unknown")
    pr_url = pr_data.get("html_url", "")
    head_sha = pr_data.get("head", {}).get("sha", "")

    repo_full_name = repo_data.get("full_name", "")
    repo_name = repo_data.get("name", "")
    repo_owner = repo_data.get("owner", {}).get("login", "")
    github_repo_id = repo_data.get("id", 0)
    installation_id = installation.get("id", 0)

    logger.info(
        "pr_review_triggered",
        repo=repo_full_name,
        pr=pr_number,
        action=action,
        author=pr_author,
    )

    # Run the review in background so webhook responds fast
    asyncio.create_task(
        _run_review(
            installation_id=installation_id,
            github_repo_id=github_repo_id,
            repo_full_name=repo_full_name,
            repo_name=repo_name,
            repo_owner=repo_owner,
            pr_number=pr_number,
            pr_title=pr_title,
            pr_author=pr_author,
            pr_url=pr_url,
            head_sha=head_sha,
        )
    )

    return {"status": "review_queued", "pr": pr_number, "repo": repo_full_name}


async def handle_installation_event(payload: dict) -> dict:
    """Handle app installation/uninstallation events."""
    action = payload.get("action", "")
    installation = payload.get("installation", {})
    installation_id = installation.get("id", 0)

    if action == "created":
        repos = payload.get("repositories", [])
        with get_db_context() as db:
            for r in repos:
                repo_db.get_or_create_repo(
                    db=db,
                    github_repo_id=r.get("id", 0),
                    name=r.get("name", ""),
                    owner=installation.get("account", {}).get("login", ""),
                    full_name=r.get("full_name", ""),
                    installation_id=installation_id,
                )
        logger.info("app_installed", repos=len(repos), installation_id=installation_id)
        return {"status": "installed", "repos": len(repos)}

    elif action == "deleted":
        logger.info("app_uninstalled", installation_id=installation_id)
        return {"status": "uninstalled"}

    return {"status": "ignored", "action": action}


async def _run_review(
    installation_id: int,
    github_repo_id: int,
    repo_full_name: str,
    repo_name: str,
    repo_owner: str,
    pr_number: int,
    pr_title: str,
    pr_author: str,
    pr_url: str,
    head_sha: str,
) -> None:
    """Execute the full review pipeline (runs as background task)."""
    review_id = None

    try:
        # 1. Ensure repo exists in DB
        with get_db_context() as db:
            repo = repo_db.get_or_create_repo(
                db=db,
                github_repo_id=github_repo_id,
                name=repo_name,
                owner=repo_owner,
                full_name=repo_full_name,
                installation_id=installation_id,
            )

            # 2. Create review record
            review = repo_db.create_review(
                db=db,
                repo_id=repo.id,
                pr_number=pr_number,
                pr_title=pr_title,
                pr_author=pr_author,
                pr_url=pr_url,
                head_sha=head_sha,
            )
            review_id = review.id

        # 3. Fetch PR diff (blocking GitHub API call)
        loop = asyncio.get_event_loop()
        gh_client = GitHubClient(installation_id)
        file_diffs = await loop.run_in_executor(
            _executor,
            gh_client.get_pr_diff,
            repo_full_name,
            pr_number,
        )

        # 4. Update status to in_progress
        with get_db_context() as db:
            repo_db.update_review_status(db, review_id, status="in_progress")

        # 5. Run the AI review
        engine = ReviewEngine()
        result = await engine.review_pr(files=file_diffs, pr_title=pr_title)

        # 6. Save issues to DB
        with get_db_context() as db:
            issue_dicts = [
                {
                    "file_path": i.file_path,
                    "line_number": i.line_number,
                    "end_line_number": i.end_line_number,
                    "severity": i.severity,
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "suggestion": i.suggestion,
                    "code_snippet": i.code_snippet,
                    "confidence": i.confidence,
                }
                for i in result.all_issues
            ]
            db_issues = repo_db.create_issues(db, review_id, issue_dicts)

        # 7. Post summary comment to GitHub
        await loop.run_in_executor(
            _executor,
            gh_client.post_review_summary,
            repo_full_name,
            pr_number,
            result,
        )

        # 8. Post inline comments
        posted_indices = await loop.run_in_executor(
            _executor,
            gh_client.post_inline_comments,
            repo_full_name,
            pr_number,
            result.all_issues,
            head_sha,
            file_diffs,
        )

        # 9. Mark posted issues in DB
        with get_db_context() as db:
            for idx in posted_indices:
                if idx < len(db_issues):
                    repo_db.mark_issue_posted(db, db_issues[idx].id)

            # 10. Update review as completed
            repo_db.update_review_status(
                db,
                review_id,
                status="completed",
                review_duration_ms=0,  # Engine tracks this internally
                llm_provider=engine.llm.provider_name,
                model_used=engine.llm.model_name,
                total_tokens_used=engine.total_tokens,
                files_reviewed=len(result.file_results),
            )

        logger.info(
            "review_completed",
            review_id=review_id,
            repo=repo_full_name,
            pr=pr_number,
            issues=result.total_issues,
        )

    except Exception as e:
        logger.error(
            "review_failed",
            review_id=review_id,
            repo=repo_full_name,
            pr=pr_number,
            error=str(e),
        )
        if review_id:
            with get_db_context() as db:
                repo_db.update_review_status(
                    db,
                    review_id,
                    status="failed",
                    error_message=str(e),
                )

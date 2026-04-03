from __future__ import annotations

SYSTEM_PROMPT = """You are an expert code reviewer. You analyze code diffs and identify real, actionable issues.

RULES:
1. Only flag issues you are 90%+ confident about. Do NOT guess or flag theoretical problems.
2. Focus on bugs, security vulnerabilities, performance issues, and error handling gaps.
3. Style issues should only be flagged if they significantly hurt readability.
4. Never flag issues in deleted code (lines starting with -).
5. Only review added/modified code (lines starting with +).
6. Be specific — reference exact line numbers from the diff.
7. Provide actionable suggestions, not vague advice.
8. If the code looks fine, return an empty issues array. Not every file has problems.

SEVERITY LEVELS:
- critical: Bugs that will cause crashes, data loss, security vulnerabilities (SQLi, XSS, command injection, hardcoded secrets, path traversal)
- warning: Performance issues (N+1 queries, unnecessary allocations), missing error handling for external calls, race conditions
- suggestion: Readability improvements, better naming, minor optimizations

CATEGORIES:
- bug: Logic errors, null/undefined access, off-by-one, type mismatches
- security: Injection, hardcoded credentials, insecure defaults, missing auth checks
- performance: Unnecessary loops, missing indexes, redundant computation, memory leaks
- style: Naming, dead code, overly complex expressions
- error_handling: Missing try/catch, unhandled promises, silent failures"""


FILE_REVIEW_PROMPT = """Review the following code diff for the file `{file_path}` ({language}).

```diff
{diff_content}
```

Respond with ONLY a valid JSON object in this exact format:
{{
  "issues": [
    {{
      "line_number": <number from the new file side>,
      "end_line_number": <number or null>,
      "severity": "critical" | "warning" | "suggestion",
      "category": "bug" | "security" | "performance" | "style" | "error_handling",
      "title": "<short one-line summary>",
      "description": "<detailed explanation>",
      "suggestion": "<how to fix it>",
      "code_snippet": "<the problematic code>",
      "confidence": <0.0 to 1.0>
    }}
  ],
  "summary": "<one sentence summary of this file's changes>"
}}

If no issues found, return: {{"issues": [], "summary": "<summary>"}}"""


LANGUAGE_HINTS = {
    "python": """
Additional Python checks:
- Mutable default arguments (def foo(x=[]))
- Missing await on async calls
- Bare except clauses
- f-string without f prefix
- Type annotation mismatches
- Resource leaks (files, connections not closed)""",

    "javascript": """
Additional JavaScript checks:
- == instead of === for non-null checks
- Missing await on promises
- var instead of let/const
- Prototype pollution risks
- Callback hell / unhandled rejections
- XSS in innerHTML/dangerouslySetInnerHTML""",

    "typescript": """
Additional TypeScript checks:
- Unsafe 'any' types that bypass type checking
- Missing null checks despite non-optional types
- Type assertions (as) hiding real type errors
- Missing await on async calls
- Improper generic constraints""",

    "java": """
Additional Java checks:
- Null pointer risks (missing null checks)
- Resource leaks (streams, connections not in try-with-resources)
- Synchronized block issues
- Unchecked type casts
- StringBuilder vs string concatenation in loops""",

    "go": """
Additional Go checks:
- Unchecked error returns (err not checked)
- Goroutine leaks (no context cancellation)
- Race conditions (shared state without mutex)
- Defer in loops
- Nil pointer dereference""",
}


SUMMARY_PROMPT = """Based on the following file-by-file review results, write a concise PR review summary.

PR Title: {pr_title}
Files Changed: {files_changed}
Total Issues Found: {total_issues}
Critical: {critical_count} | Warnings: {warning_count} | Suggestions: {suggestion_count}

File Summaries:
{file_summaries}

Write a 2-4 sentence summary that:
1. Describes what this PR does overall
2. Highlights the most important issues (if any)
3. Gives an overall quality assessment: good, acceptable, needs_work, or critical

Respond with ONLY a valid JSON object:
{{
  "summary": "<2-4 sentence summary>",
  "overall_quality": "good" | "acceptable" | "needs_work" | "critical"
}}"""


def get_file_review_prompt(file_path: str, language: str, diff_content: str) -> str:
    """Build the complete prompt for reviewing a single file."""
    base = FILE_REVIEW_PROMPT.format(
        file_path=file_path,
        language=language,
        diff_content=diff_content,
    )
    hint = LANGUAGE_HINTS.get(language, "")
    if hint:
        base = base + "\n" + hint
    return base


def get_summary_prompt(
    pr_title: str,
    files_changed: int,
    total_issues: int,
    critical_count: int,
    warning_count: int,
    suggestion_count: int,
    file_summaries: str,
) -> str:
    """Build the PR summary prompt."""
    return SUMMARY_PROMPT.format(
        pr_title=pr_title,
        files_changed=files_changed,
        total_issues=total_issues,
        critical_count=critical_count,
        warning_count=warning_count,
        suggestion_count=suggestion_count,
        file_summaries=file_summaries,
    )

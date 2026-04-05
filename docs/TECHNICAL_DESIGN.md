# AI Code Reviewer — Technical Design Document

## System Overview

AI Code Reviewer is a GitHub App that automatically reviews Pull Requests using open-source LLMs. It receives webhooks from GitHub, analyzes code diffs file-by-file, and posts inline review comments with severity-rated issues.

### High-Level Architecture

```
GitHub (webhook) → FastAPI → Diff Parser → LLM Review Engine → GitHub Comments
                                                    ↓
                                              SQLite (history)
                                                    ↓
                                            React Dashboard
```

---

## Design Decisions & Trade-offs

### 1. Why File-by-File Review Instead of Full-PR Review?

**Decision:** Each file is reviewed independently in a separate LLM call.

**Why:**
- Open-source models have limited context windows (8K-32K tokens). A PR with 20 files and 2000+ lines won't fit in one call.
- File-level review produces more focused, accurate feedback than trying to understand the entire PR at once.
- If one file review fails (rate limit, timeout), other files still get reviewed.

**Trade-off:** The LLM can't detect cross-file issues (e.g., function renamed in file A but not updated in file B). This would require a second "cross-file analysis" pass — planned for future.

### 2. Why Groq Over Direct Ollama for Default?

**Decision:** Default provider is Groq (cloud), with Ollama as self-hosted option.

**Why:**
- Groq offers free Llama 3.3 70B inference — much stronger than what most laptops can run locally via Ollama.
- Groq latency is ~2 seconds for a review. Ollama on CPU can take 30-60 seconds per file.
- For a portfolio demo, speed matters — reviewer sees results in seconds, not minutes.

**Trade-off:** Groq has rate limits (30 req/min). For repos with many PRs, the queue can back up. Ollama has no limits but is slower.

### 3. Why SQLite Instead of PostgreSQL?

**Decision:** SQLite for persistence.

**Why:**
- Zero setup — no database server needed. One file (`reviews.db`).
- Perfect for single-server deployment (Railway/Render free tier).
- Reduces Docker Compose complexity (no DB container).

**Trade-off:** Can't handle concurrent writes well. If 10 PRs come in simultaneously, writes may conflict. For production scale, migrate to PostgreSQL.

### 4. Why Background Task Instead of Queue (Celery/Redis)?

**Decision:** Review runs as an `asyncio.create_task()` background task, not a proper job queue.

**Why:**
- Simplicity — no Redis, no Celery worker, no extra infrastructure.
- For a portfolio project with low volume, this is sufficient.
- Webhook responds immediately (200 OK), review happens async.

**Trade-off:** If the server restarts during a review, that review is lost. No retry mechanism. A production system would use Celery + Redis with dead-letter queues.

---

## Known Gaps & Solutions

### Gap 1: Large PR Handling

**Problem:** A PR with 100+ files and 5000+ lines of changes. Even with file-by-file review, this means 100 LLM calls.

**Impact:** Groq rate limit (30/min) means a 100-file PR takes 3+ minutes. User waiting for review.

**Current mitigation:**
- `max_files_per_review` setting (default: 50) caps files reviewed.
- Files sorted by change count — most-changed files reviewed first.
- Non-code files (lock files, images, configs) auto-skipped.

**Future solution:**
- Priority tiers: review critical files first (security-sensitive paths like `auth/`, `payment/`), defer style-only files.
- Chunked review with progress updates via GitHub check status API.
- Caching: if a file was reviewed in a previous PR and hasn't changed, skip it.

### Gap 2: LLM Hallucinating Line Numbers

**Problem:** LLM says "bug on line 45" but line 45 doesn't exist in the diff or contains unrelated code.

**Impact:** Inline comment posted on wrong line — confusing for the developer.

**Current mitigation:**
- After LLM returns issues, each `line_number` is validated against the actual diff's `changed_line_numbers`.
- If line is within 5 lines of a valid changed line, snap to nearest valid line.
- If line is too far off, drop the inline comment but keep the issue in the summary comment.

**Future solution:**
- Include line numbers explicitly in the prompt context so the LLM has less room to hallucinate.
- Post-processing: verify the `code_snippet` returned by LLM actually exists in the diff at the claimed line.

### Gap 3: False Positives (Noisy Reviews)

**Problem:** Bot posts 20 comments on every PR, most are nitpicks. Developer gets annoyed and uninstalls.

**Impact:** User churn. The #1 reason code review bots fail.

**Current mitigation:**
- Confidence threshold: issues below 70% confidence are dropped.
- Severity filter: only `critical` and `warning` posted as inline comments by default. `suggestion` only appears in the summary.
- Prompt instructs LLM: "Only flag issues you are 90%+ confident about."

**Future solution:**
- Feedback loop: developer can react to comments (thumbs up/down). Track accuracy per issue category. Lower confidence threshold for high-accuracy categories, raise it for noisy ones.
- Per-repo learning: after 10 reviews, the system knows which types of issues this repo cares about.

### Gap 4: Cross-File Issues Not Detected

**Problem:** Function signature changed in `utils.py` but callers in `main.py` not updated. Bot reviews each file independently and misses this.

**Impact:** Misses real bugs that span multiple files.

**Current mitigation:** None. Each file reviewed independently.

**Future solution:**
- Two-pass review: Pass 1 reviews each file. Pass 2 sends a summary of all files + their issues to the LLM with the prompt: "Based on these file changes, are there any cross-file consistency issues?"
- This second pass only needs summaries (~200 tokens/file), not full diffs, so context window is manageable.

### Gap 5: No Review for Config/Infrastructure Changes

**Problem:** Changes to `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `.env.example` are skipped because they're not in the "code" extension list.

**Impact:** Security misconfigurations (exposed ports, missing env vars, debug mode enabled) go unreviewed.

**Current mitigation:** Only files with known code extensions are reviewed.

**Future solution:**
- Add config-specific review prompts for Docker, nginx, CI/CD files.
- Different severity criteria: for configs, focus on security (exposed ports, debug flags, hardcoded credentials).

### Gap 6: Rate Limit Exhaustion Under Load

**Problem:** Popular repo with 20 PRs opened simultaneously. Groq allows 30 req/min. Queue backs up, reviews delayed or fail.

**Impact:** Reviews marked as "failed" in dashboard. Developers don't get feedback.

**Current mitigation:**
- Token-bucket rate limiter (28 req/min, leaves 2 as buffer).
- Exponential backoff with 3 retries on rate limit errors.
- If all retries fail, review saved as "failed" with error message.

**Future solution:**
- Per-PR queue with priority (older PRs first).
- Status comment on GitHub: "Review queued, estimated wait: 2 minutes."
- Multi-provider fallback: if Groq is rate-limited, fall back to Ollama.
- Batch mode: for very large PRs, group multiple files into one LLM call using summaries.

### Gap 7: Webhook Reliability

**Problem:** Server restarts, ngrok disconnects, or deployment crashes. GitHub sends webhook but nobody receives it.

**Impact:** PR never gets reviewed. Silent failure — developer doesn't know.

**Current mitigation:** None beyond GitHub's built-in retry (GitHub retries failed webhooks for up to 3 days).

**Future solution:**
- Implement a "catch-up" cron job: every 5 minutes, check for open PRs on installed repos that don't have a review record → trigger review.
- Webhook delivery tracking: GitHub shows failed deliveries in the app's Advanced tab. Could poll this and re-process.

### Gap 8: No Support for Monorepo Review Policies

**Problem:** In a monorepo, different directories may need different review strictness. `/src/auth/` needs security focus, `/tests/` needs less scrutiny.

**Impact:** Same review policy applied everywhere. Auth code gets same treatment as test files.

**Current mitigation:** `.codereview.yml` supports file ignore patterns, but not per-directory review policies.

**Future solution:**
- Extend `.codereview.yml` to support path-specific rules:
  ```yaml
  rules:
    "src/auth/**":
      min_severity: suggestion
      categories: [security, bug]
    "tests/**":
      min_severity: critical
      categories: [bug]
  ```

### Gap 9: No Diff Context — Only Changed Lines Reviewed

**Problem:** LLM only sees the diff (changed lines + small context). It doesn't see the full file. Can't understand the broader code structure.

**Impact:** Misses issues where the changed code interacts with unchanged code. E.g., a new function that duplicates an existing one.

**Current mitigation:** GitHub's diff includes 3 lines of context around each change by default.

**Future solution:**
- For critical files (detected by severity of changes), fetch the full file content and include relevant portions around the diff.
- Smart context expansion: if the diff is inside a function, include the full function body.

---

## Future Roadmap

### Phase 1: Quality Improvements
- [ ] Cross-file analysis (two-pass review)
- [ ] Feedback loop (thumbs up/down on comments)
- [ ] Config file review support (Docker, CI/CD, nginx)
- [ ] Smart context expansion (include full function body)

### Phase 2: Scale & Reliability
- [ ] PostgreSQL migration for concurrent writes
- [ ] Celery + Redis job queue for review processing
- [ ] Catch-up cron job for missed webhooks
- [ ] Multi-provider fallback (Groq → Ollama automatic switch)

### Phase 3: Intelligence
- [ ] Per-repo learning (track which issue types are useful per repo)
- [ ] Custom review rules (user-defined patterns to always flag)
- [ ] Auto-fix suggestions with one-click "Apply fix" button
- [ ] PR summary: "This PR does X, Y, Z" — generated from the diff

### Phase 4: Enterprise Features
- [ ] GitLab support (in addition to GitHub)
- [ ] Team dashboard (org-wide review stats)
- [ ] Review SLA tracking (time from PR open to review posted)
- [ ] SSO authentication for the dashboard

---

## Performance Characteristics

| Metric | Current | Target |
|--------|---------|--------|
| Time to first comment | 5-10 seconds | < 5 seconds |
| Files per minute | ~15 (Groq rate limited) | ~30 (with caching) |
| Max files per PR | 50 (configurable) | 100+ (with priority tiers) |
| False positive rate | ~20% (estimated) | < 10% (with feedback loop) |
| Supported languages | 5 (Python, JS, TS, Java, Go) | 10+ |

---

## Security Considerations

1. **Code privacy:** Diffs are sent to Groq's API. For sensitive code, use Ollama (fully local, nothing leaves the machine).
2. **Webhook signature verification:** Every webhook is verified using HMAC-SHA256 to prevent spoofing.
3. **Installation tokens:** Auto-expire after 1 hour. Cached but never stored on disk.
4. **No code storage:** Diffs are processed in memory and discarded. Only review results (issues, summaries) are persisted.
5. **Private key:** The `.pem` file is in `.gitignore` and never committed to the repo.

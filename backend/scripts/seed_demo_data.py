"""
Seed demo data for testing the UI end-to-end.
Run: python3 scripts/seed_demo_data.py

This creates realistic review data so you can see
the full dashboard, review detail, and analytics pages.
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import init_db, get_db_context
from app.db import repository as repo_db

def seed():
    print("Initializing database...")
    init_db()

    with get_db_context() as db:
        # ── Create repos ──
        print("Creating repos...")
        repo1 = repo_db.get_or_create_repo(
            db=db,
            github_repo_id=100001,
            name="ai-code-reviewer",
            owner="Ravi10048",
            full_name="Ravi10048/ai-code-reviewer",
            installation_id=1,
        )
        repo2 = repo_db.get_or_create_repo(
            db=db,
            github_repo_id=100002,
            name="fastapi-starter",
            owner="Ravi10048",
            full_name="Ravi10048/fastapi-starter",
            installation_id=1,
        )

        now = datetime.now(timezone.utc)

        # ── Review 1: PR with critical issues ──
        print("Creating review 1 — critical security issues...")
        review1 = repo_db.create_review(
            db=db,
            repo_id=repo1.id,
            pr_number=12,
            pr_title="Add user authentication endpoint",
            pr_author="developer1",
            pr_url="https://github.com/Ravi10048/ai-code-reviewer/pull/12",
            head_sha="abc123def456",
        )
        repo_db.update_review_status(
            db, review1.id,
            status="completed",
            review_duration_ms=8500,
            llm_provider="groq",
            model_used="llama-3.1-70b-versatile",
            total_tokens_used=4200,
            files_reviewed=3,
        )
        repo_db.create_issues(db, review1.id, [
            {
                "file_path": "src/auth/login.py",
                "line_number": 45,
                "end_line_number": None,
                "severity": "critical",
                "category": "security",
                "title": "SQL injection vulnerability in login query",
                "description": "User input is directly interpolated into the SQL query string without parameterization. An attacker could inject malicious SQL to bypass authentication or extract data.",
                "suggestion": "Use parameterized queries: db.execute('SELECT * FROM users WHERE email = ?', (email,))",
                "code_snippet": "query = f\"SELECT * FROM users WHERE email = '{email}'\"",
                "confidence": 0.95,
                "posted_to_github": True,
            },
            {
                "file_path": "src/auth/login.py",
                "line_number": 72,
                "end_line_number": None,
                "severity": "critical",
                "category": "security",
                "title": "Hardcoded JWT secret key",
                "description": "The JWT secret key is hardcoded in the source code. This is a security vulnerability as anyone with access to the code can forge tokens.",
                "suggestion": "Move the secret to an environment variable: os.environ['JWT_SECRET']",
                "code_snippet": "SECRET_KEY = 'my-super-secret-key-123'",
                "confidence": 0.98,
                "posted_to_github": True,
            },
            {
                "file_path": "src/auth/middleware.py",
                "line_number": 23,
                "end_line_number": None,
                "severity": "warning",
                "category": "error_handling",
                "title": "Missing token expiry validation",
                "description": "The JWT token is decoded but the expiry time (exp) is not checked. Expired tokens will still be accepted.",
                "suggestion": "Add verify_exp=True to jwt.decode() options",
                "code_snippet": "payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])",
                "confidence": 0.88,
                "posted_to_github": True,
            },
            {
                "file_path": "src/auth/middleware.py",
                "line_number": 51,
                "end_line_number": None,
                "severity": "suggestion",
                "category": "style",
                "title": "Broad exception catch hides errors",
                "description": "Catching all exceptions masks specific JWT errors (expired, invalid signature, malformed). Consider catching specific exceptions.",
                "suggestion": "Catch jwt.ExpiredSignatureError, jwt.InvalidTokenError separately",
                "code_snippet": "except Exception:\n    return None",
                "confidence": 0.82,
                "posted_to_github": False,
            },
        ])

        # ── Review 2: Clean PR ──
        print("Creating review 2 — clean PR...")
        review2 = repo_db.create_review(
            db=db,
            repo_id=repo1.id,
            pr_number=13,
            pr_title="Refactor database connection pooling",
            pr_author="developer2",
            pr_url="https://github.com/Ravi10048/ai-code-reviewer/pull/13",
            head_sha="def789ghi012",
        )
        repo_db.update_review_status(
            db, review2.id,
            status="completed",
            review_duration_ms=5200,
            llm_provider="groq",
            model_used="llama-3.1-70b-versatile",
            total_tokens_used=2800,
            files_reviewed=2,
        )

        # ── Review 3: Performance issues ──
        print("Creating review 3 — performance warnings...")
        review3 = repo_db.create_review(
            db=db,
            repo_id=repo2.id,
            pr_number=7,
            pr_title="Add product search with filters",
            pr_author="developer1",
            pr_url="https://github.com/Ravi10048/fastapi-starter/pull/7",
            head_sha="ghi345jkl678",
        )
        repo_db.update_review_status(
            db, review3.id,
            status="completed",
            review_duration_ms=12300,
            llm_provider="groq",
            model_used="llama-3.1-70b-versatile",
            total_tokens_used=6100,
            files_reviewed=5,
        )
        repo_db.create_issues(db, review3.id, [
            {
                "file_path": "src/products/search.py",
                "line_number": 34,
                "end_line_number": 42,
                "severity": "warning",
                "category": "performance",
                "title": "N+1 query in product search loop",
                "description": "Each product in the search results triggers a separate query to fetch its category. With 100 results, this makes 101 database queries instead of 1.",
                "suggestion": "Use JOIN or eager loading: db.query(Product).options(joinedload(Product.category)).filter(...)",
                "code_snippet": "for product in products:\n    category = db.query(Category).filter(Category.id == product.category_id).first()",
                "confidence": 0.92,
                "posted_to_github": True,
            },
            {
                "file_path": "src/products/search.py",
                "line_number": 78,
                "end_line_number": None,
                "severity": "warning",
                "category": "performance",
                "title": "Missing database index on search column",
                "description": "The 'name' column is used in LIKE queries but doesn't have an index. This will cause full table scans on large datasets.",
                "suggestion": "Add an index: CREATE INDEX idx_products_name ON products(name)",
                "code_snippet": "products = db.query(Product).filter(Product.name.like(f'%{query}%')).all()",
                "confidence": 0.85,
                "posted_to_github": True,
            },
            {
                "file_path": "src/products/models.py",
                "line_number": 15,
                "end_line_number": None,
                "severity": "suggestion",
                "category": "bug",
                "title": "Price field allows negative values",
                "description": "The price column has no constraint preventing negative values. A product could accidentally be assigned a negative price.",
                "suggestion": "Add CheckConstraint: CheckConstraint('price >= 0', name='positive_price')",
                "code_snippet": "price = Column(Float, nullable=False)",
                "confidence": 0.78,
                "posted_to_github": False,
            },
        ])

        # ── Review 4: In progress ──
        print("Creating review 4 — in progress...")
        review4 = repo_db.create_review(
            db=db,
            repo_id=repo2.id,
            pr_number=8,
            pr_title="Implement WebSocket real-time notifications",
            pr_author="developer3",
            pr_url="https://github.com/Ravi10048/fastapi-starter/pull/8",
            head_sha="jkl901mno234",
        )
        repo_db.update_review_status(db, review4.id, status="in_progress")

        # ── Review 5: Failed ──
        print("Creating review 5 — failed review...")
        review5 = repo_db.create_review(
            db=db,
            repo_id=repo1.id,
            pr_number=14,
            pr_title="Update dependencies and fix CVEs",
            pr_author="dependabot",
            pr_url="https://github.com/Ravi10048/ai-code-reviewer/pull/14",
            head_sha="mno567pqr890",
        )
        repo_db.update_review_status(
            db, review5.id,
            status="failed",
            error_message="Groq rate limit exceeded. Retry in 60 seconds.",
        )

        # ── Review 6: Another completed one for analytics ──
        print("Creating review 6 — bug fix PR...")
        review6 = repo_db.create_review(
            db=db,
            repo_id=repo1.id,
            pr_number=15,
            pr_title="Fix race condition in concurrent file uploads",
            pr_author="developer2",
            pr_url="https://github.com/Ravi10048/ai-code-reviewer/pull/15",
            head_sha="pqr123stu456",
        )
        repo_db.update_review_status(
            db, review6.id,
            status="completed",
            review_duration_ms=6800,
            llm_provider="groq",
            model_used="llama-3.1-70b-versatile",
            total_tokens_used=3400,
            files_reviewed=2,
        )
        repo_db.create_issues(db, review6.id, [
            {
                "file_path": "src/upload/handler.py",
                "line_number": 89,
                "end_line_number": 95,
                "severity": "critical",
                "category": "bug",
                "title": "Race condition in file write — data corruption possible",
                "description": "Multiple concurrent uploads to the same path can interleave writes, corrupting the output file. No file lock or atomic write is used.",
                "suggestion": "Use a temporary file and atomic rename: write to a .tmp file, then os.rename() to the final path",
                "code_snippet": "with open(upload_path, 'wb') as f:\n    while chunk := await file.read(8192):\n        f.write(chunk)",
                "confidence": 0.91,
                "posted_to_github": True,
            },
            {
                "file_path": "src/upload/handler.py",
                "line_number": 112,
                "end_line_number": None,
                "severity": "warning",
                "category": "error_handling",
                "title": "Uploaded file not cleaned up on processing failure",
                "description": "If post-processing raises an exception, the uploaded file remains on disk. Over time this will consume storage.",
                "suggestion": "Add a try/finally block to delete the file if processing fails",
                "code_snippet": "process_file(upload_path)  # if this fails, file stays",
                "confidence": 0.87,
                "posted_to_github": True,
            },
        ])

    print("\n=== Demo data seeded successfully! ===")
    print("  - 2 repos")
    print("  - 6 reviews (3 completed, 1 clean, 1 in-progress, 1 failed)")
    print("  - 9 issues (3 critical, 4 warning, 2 suggestion)")
    print("\nStart the server and open http://localhost:8090/docs or the frontend!")


if __name__ == "__main__":
    seed()

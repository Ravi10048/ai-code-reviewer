from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.exceptions import DiffParseError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Regex for unified diff hunk headers: @@ -old_start,old_count +new_start,new_count @@
HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$"
)

# File extensions we want to review
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
    ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".zsh", ".yaml", ".yml", ".toml", ".json", ".sql",
    ".html", ".css", ".scss", ".vue", ".svelte",
}

# Files to always skip
SKIP_PATTERNS = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Pipfile.lock", "Cargo.lock", "go.sum", "composer.lock",
    ".min.js", ".min.css", ".map",
}


@dataclass
class DiffLine:
    """A single line in a diff hunk."""

    content: str
    old_line_number: int | None  # None for additions
    new_line_number: int | None  # None for deletions
    line_type: str  # "addition", "deletion", "context"


@dataclass
class DiffHunk:
    """A contiguous block of changes within a file."""

    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    section_header: str  # Function/class name from @@ line
    lines: list[DiffLine] = field(default_factory=list)

    @property
    def raw_text(self) -> str:
        """Reconstruct the hunk as unified diff text."""
        parts = [self.header]
        for line in self.lines:
            if line.line_type == "addition":
                parts.append(f"+{line.content}")
            elif line.line_type == "deletion":
                parts.append(f"-{line.content}")
            else:
                parts.append(f" {line.content}")
        return "\n".join(parts)


@dataclass
class FileDiff:
    """Parsed diff for a single file."""

    file_path: str
    old_path: str | None  # None for new files
    status: str  # "added", "modified", "deleted", "renamed"
    language: str
    hunks: list[DiffHunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0

    @property
    def total_changes(self) -> int:
        return self.additions + self.deletions

    @property
    def raw_diff(self) -> str:
        """Full diff text for this file."""
        return "\n".join(hunk.raw_text for hunk in self.hunks)

    @property
    def changed_line_numbers(self) -> list[int]:
        """New-side line numbers that were added or modified."""
        lines = []
        for hunk in self.hunks:
            for line in hunk.lines:
                if line.line_type == "addition" and line.new_line_number:
                    lines.append(line.new_line_number)
        return sorted(lines)

    def get_hunk_for_line(self, line_number: int) -> DiffHunk | None:
        """Find the hunk containing a specific new-side line number."""
        for hunk in self.hunks:
            hunk_end = hunk.new_start + hunk.new_count
            if hunk.new_start <= line_number < hunk_end:
                return hunk
        return None


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".jsx": "javascript", ".java": "java",
        ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
        ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
        ".scala": "scala", ".sh": "shell", ".bash": "shell",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".json": "json", ".sql": "sql", ".html": "html",
        ".css": "css", ".scss": "scss", ".vue": "vue", ".svelte": "svelte",
    }
    for ext, lang in ext_map.items():
        if file_path.endswith(ext):
            return lang
    return "unknown"


def should_review_file(file_path: str) -> bool:
    """Check if a file should be included in the review."""
    # Skip known non-code files
    for pattern in SKIP_PATTERNS:
        if file_path.endswith(pattern):
            return False

    # Skip binary/generated paths
    skip_dirs = {"node_modules/", "vendor/", "dist/", "build/", ".git/", "__pycache__/"}
    for skip in skip_dirs:
        if skip in file_path:
            return False

    # Check extension
    for ext in CODE_EXTENSIONS:
        if file_path.endswith(ext):
            return True

    return False


def parse_diff(raw_diff: str) -> list[FileDiff]:
    """Parse a complete unified diff into structured FileDiff objects.

    Handles standard GitHub PR diff format:
        diff --git a/path b/path
        --- a/path
        +++ b/path
        @@ ... @@
        ...
    """
    if not raw_diff or not raw_diff.strip():
        return []

    files: list[FileDiff] = []
    current_file: FileDiff | None = None
    current_hunk: DiffHunk | None = None

    lines = raw_diff.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # New file diff header
        if line.startswith("diff --git "):
            # Save previous file
            if current_file and current_file.hunks:
                files.append(current_file)

            # Parse file paths: diff --git a/old_path b/new_path
            parts = line.split(" b/", 1)
            if len(parts) == 2:
                new_path = parts[1]
                old_parts = parts[0].split(" a/", 1)
                old_path = old_parts[1] if len(old_parts) == 2 else None
            else:
                i += 1
                continue

            current_file = FileDiff(
                file_path=new_path,
                old_path=old_path,
                status="modified",
                language=detect_language(new_path),
            )
            current_hunk = None
            i += 1
            continue

        # Detect file status from --- and +++ lines
        if current_file:
            if line.startswith("--- /dev/null"):
                current_file.status = "added"
                i += 1
                continue
            if line.startswith("+++ /dev/null"):
                current_file.status = "deleted"
                i += 1
                continue
            if line.startswith("--- ") or line.startswith("+++ "):
                i += 1
                continue
            if line.startswith("rename from "):
                current_file.status = "renamed"
                i += 1
                continue
            if line.startswith("rename to ") or line.startswith("index ") or line.startswith("new file") or line.startswith("deleted file"):
                i += 1
                continue

        # Hunk header
        hunk_match = HUNK_HEADER_RE.match(line)
        if hunk_match and current_file:
            current_hunk = DiffHunk(
                header=line,
                old_start=int(hunk_match.group(1)),
                old_count=int(hunk_match.group(2) or 1),
                new_start=int(hunk_match.group(3)),
                new_count=int(hunk_match.group(4) or 1),
                section_header=hunk_match.group(5).strip(),
            )
            current_file.hunks.append(current_hunk)
            # Reset line counters for this hunk
            _old_line = current_hunk.old_start
            _new_line = current_hunk.new_start
            i += 1
            continue

        # Diff content lines
        if current_hunk and current_file:
            if line.startswith("+"):
                diff_line = DiffLine(
                    content=line[1:],
                    old_line_number=None,
                    new_line_number=_new_line,
                    line_type="addition",
                )
                current_hunk.lines.append(diff_line)
                current_file.additions += 1
                _new_line += 1
            elif line.startswith("-"):
                diff_line = DiffLine(
                    content=line[1:],
                    old_line_number=_old_line,
                    new_line_number=None,
                    line_type="deletion",
                )
                current_hunk.lines.append(diff_line)
                current_file.deletions += 1
                _old_line += 1
            elif line.startswith(" "):
                diff_line = DiffLine(
                    content=line[1:],
                    old_line_number=_old_line,
                    new_line_number=_new_line,
                    line_type="context",
                )
                current_hunk.lines.append(diff_line)
                _old_line += 1
                _new_line += 1
            elif line.startswith("\\"):
                # "\ No newline at end of file" — skip
                pass

        i += 1

    # Don't forget the last file
    if current_file and current_file.hunks:
        files.append(current_file)

    logger.info("diff_parsed", total_files=len(files))
    return files


def filter_reviewable_files(
    files: list[FileDiff], max_files: int = 0
) -> list[FileDiff]:
    """Filter files to only those worth reviewing, respecting limits."""
    reviewable = [f for f in files if should_review_file(f.file_path)]

    # Sort by changes (most changes first — review the important stuff)
    reviewable.sort(key=lambda f: f.total_changes, reverse=True)

    if max_files > 0:
        reviewable = reviewable[:max_files]

    logger.info(
        "files_filtered",
        total=len(files),
        reviewable=len(reviewable),
        skipped=len(files) - len(reviewable),
    )
    return reviewable

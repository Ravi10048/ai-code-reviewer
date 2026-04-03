"""Tests for the unified diff parser."""
import pytest
from app.github.diff_parser import (
    parse_diff,
    detect_language,
    should_review_file,
    filter_reviewable_files,
)

SAMPLE_DIFF = """diff --git a/src/utils.py b/src/utils.py
--- a/src/utils.py
+++ b/src/utils.py
@@ -10,6 +10,8 @@ def helper():
     x = 1
     y = 2
     return x + y
+    z = 3
+    return z

 def other():
     pass
@@ -20,3 +22,5 @@ def other():
     a = 1
-    b = 2
+    b = 3
+    c = 4
     return a
"""

NEW_FILE_DIFF = """diff --git a/src/new_file.py b/src/new_file.py
new file mode 100644
--- /dev/null
+++ b/src/new_file.py
@@ -0,0 +1,5 @@
+def hello():
+    print("hello")
+
+def world():
+    print("world")
"""

MULTI_FILE_DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 import os
+import sys

 def main():
diff --git a/test.js b/test.js
--- a/test.js
+++ b/test.js
@@ -5,3 +5,4 @@ function test() {
     const a = 1;
     const b = 2;
+    const c = 3;
     return a + b;
"""


class TestParseDiff:
    def test_parses_single_file(self):
        files = parse_diff(SAMPLE_DIFF)
        assert len(files) == 1
        assert files[0].file_path == "src/utils.py"
        assert files[0].status == "modified"
        assert files[0].language == "python"

    def test_counts_additions_and_deletions(self):
        files = parse_diff(SAMPLE_DIFF)
        f = files[0]
        assert f.additions == 4  # +z=3, +return z, +b=3, +c=4
        assert f.deletions == 1  # -b=2

    def test_parses_new_file(self):
        files = parse_diff(NEW_FILE_DIFF)
        assert len(files) == 1
        assert files[0].status == "added"
        assert files[0].additions == 5

    def test_parses_multiple_files(self):
        files = parse_diff(MULTI_FILE_DIFF)
        assert len(files) == 2
        assert files[0].file_path == "app.py"
        assert files[1].file_path == "test.js"

    def test_line_numbers_are_correct(self):
        files = parse_diff(SAMPLE_DIFF)
        f = files[0]
        added_lines = f.changed_line_numbers
        assert 13 in added_lines  # +z = 3
        assert 14 in added_lines  # +return z

    def test_hunk_lookup(self):
        files = parse_diff(SAMPLE_DIFF)
        f = files[0]
        hunk = f.get_hunk_for_line(13)
        assert hunk is not None
        assert hunk.new_start == 10

    def test_empty_diff(self):
        assert parse_diff("") == []
        assert parse_diff("   ") == []

    def test_multiple_hunks(self):
        files = parse_diff(SAMPLE_DIFF)
        assert len(files[0].hunks) == 2


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("app.py") == "python"

    def test_javascript(self):
        assert detect_language("index.js") == "javascript"

    def test_typescript(self):
        assert detect_language("App.tsx") == "typescript"

    def test_unknown(self):
        assert detect_language("Makefile") == "unknown"


class TestShouldReviewFile:
    def test_python_file(self):
        assert should_review_file("src/app.py") is True

    def test_lock_file(self):
        assert should_review_file("package-lock.json") is False

    def test_node_modules(self):
        assert should_review_file("node_modules/lib/index.js") is False

    def test_minified(self):
        assert should_review_file("dist/bundle.min.js") is False


class TestFilterReviewableFiles:
    def test_filters_non_code(self):
        files = parse_diff(MULTI_FILE_DIFF)
        # Both app.py and test.js are code files
        filtered = filter_reviewable_files(files)
        assert len(filtered) == 2

    def test_respects_max_files(self):
        files = parse_diff(MULTI_FILE_DIFF)
        filtered = filter_reviewable_files(files, max_files=1)
        assert len(filtered) == 1

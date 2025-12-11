"""Tests for parsing utilities."""


from gilfoyle.utils.parsing import (
    extract_file_paths_from_diff,
    extract_task_ids,
    sanitize_comment,
    truncate_diff,
)


class TestExtractTaskIds:
    """Tests for extract_task_ids function."""

    def test_extract_full_url(self):
        """Test extraction from full Teamwork URL."""
        text = "See https://projects.ebs-integrator.com/app/tasks/12345 for details"
        assert extract_task_ids(text) == ["12345"]

    def test_extract_hash_url(self):
        """Test extraction from hash-based URL."""
        text = "Task: https://projects.ebs-integrator.com/#/tasks/67890"
        assert extract_task_ids(text) == ["67890"]

    def test_extract_shorthand(self):
        """Test extraction from TW-XXXX shorthand."""
        text = "This implements TW-12345 and #TW-67890"
        result = extract_task_ids(text)
        assert "12345" in result
        assert "67890" in result

    def test_extract_task_reference(self):
        """Test extraction from 'task: XXXX' format."""
        text = "Related to task: 11111 and task #22222"
        result = extract_task_ids(text)
        assert "11111" in result
        assert "22222" in result

    def test_no_duplicates(self):
        """Test that duplicates are removed."""
        text = "TW-12345 and https://projects.ebs-integrator.com/app/tasks/12345"
        assert extract_task_ids(text) == ["12345"]

    def test_empty_input(self):
        """Test with empty input."""
        assert extract_task_ids("") == []
        assert extract_task_ids(None) == []

    def test_no_matches(self):
        """Test with text containing no task IDs."""
        text = "This is just a regular description without any task references."
        assert extract_task_ids(text) == []


class TestSanitizeComment:
    """Tests for sanitize_comment function."""

    def test_removes_script_tags(self):
        """Test that script tags are removed."""
        text = "Hello <script>alert('xss')</script> World"
        result = sanitize_comment(text)
        assert "<script>" not in result
        assert "alert" not in result

    def test_escapes_html(self):
        """Test that HTML is escaped."""
        text = "<div>Test</div>"
        result = sanitize_comment(text)
        assert "&lt;div&gt;" in result

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        text = "  Hello World  "
        assert sanitize_comment(text) == "Hello World"


class TestTruncateDiff:
    """Tests for truncate_diff function."""

    def test_no_truncation_needed(self):
        """Test that short diffs are not truncated."""
        diff = "line1\nline2\nline3"
        assert truncate_diff(diff, max_lines=10) == diff

    def test_truncation(self):
        """Test that long diffs are truncated."""
        lines = [f"line{i}" for i in range(100)]
        diff = "\n".join(lines)
        result = truncate_diff(diff, max_lines=10)
        assert "truncated" in result
        assert "90 more lines" in result

    def test_exact_limit(self):
        """Test with exactly max_lines."""
        lines = [f"line{i}" for i in range(10)]
        diff = "\n".join(lines)
        assert truncate_diff(diff, max_lines=10) == diff


class TestExtractFilePathsFromDiff:
    """Tests for extract_file_paths_from_diff function."""

    def test_extract_single_file(self):
        """Test extraction from single file diff."""
        diff = """diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,5 @@
 def main():
     pass
"""
        paths = extract_file_paths_from_diff(diff)
        assert paths == ["src/main.py"]

    def test_extract_multiple_files(self):
        """Test extraction from multi-file diff."""
        diff = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1 +1 @@
-old
+new
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1 +1 @@
-old
+new
"""
        paths = extract_file_paths_from_diff(diff)
        assert "file1.py" in paths
        assert "file2.py" in paths

    def test_no_files(self):
        """Test with empty diff."""
        assert extract_file_paths_from_diff("") == []

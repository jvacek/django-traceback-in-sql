"""Tests for SQL comment formatting (isolated from frame capture logic).

This module tests only the string formatting of stack frames into SQL comments.
Functional tests (frame capture, filtering, etc.) are in other test files.
"""

from sql_traceback.parser import format_stacktrace_comment
from sql_traceback.traceback_info import StackFrame


def test_format_single_frame():
    """Test formatting a single stack frame."""
    frames = [StackFrame(path="/app/views.py", line=42, name="my_view")]

    result = format_stacktrace_comment(frames)

    assert "/*" in result
    assert "STACKTRACE:" in result
    assert "*/" in result
    assert "# /app/views.py:42 in my_view" in result


def test_format_multiple_frames():
    """Test formatting multiple stack frames."""
    frames = [
        StackFrame(path="/app/views.py", line=42, name="my_view"),
        StackFrame(path="/app/models.py", line=100, name="save"),
        StackFrame(path="/app/utils.py", line=15, name="helper"),
    ]

    result = format_stacktrace_comment(frames)

    # Verify all frames are present
    assert "# /app/views.py:42 in my_view" in result
    assert "# /app/models.py:100 in save" in result
    assert "# /app/utils.py:15 in helper" in result

    # Verify proper structure
    assert result.startswith("\n/*\nSTACKTRACE:\n")
    assert result.endswith("\n*/")


def test_format_empty_frames():
    """Test formatting with no frames returns empty string."""
    result = format_stacktrace_comment([])

    assert result == ""


def test_format_frame_with_special_characters():
    """Test formatting frames with special characters in paths."""
    frames = [
        StackFrame(path="/app/my-project/views.py", line=1, name="test_function"),
        StackFrame(path="/app/project (copy)/models.py", line=2, name="__init__"),
    ]

    result = format_stacktrace_comment(frames)

    # Special characters should be preserved
    assert "# /app/my-project/views.py:1 in test_function" in result
    assert "# /app/project (copy)/models.py:2 in __init__" in result


def test_format_multiline_structure():
    """Test that formatting produces proper multiline SQL comment."""
    frames = [
        StackFrame(path="/app/a.py", line=1, name="func_a"),
        StackFrame(path="/app/b.py", line=2, name="func_b"),
    ]

    result = format_stacktrace_comment(frames)

    lines = result.split("\n")

    # Verify structure
    assert lines[0] == ""  # Leading newline
    assert lines[1] == "/*"
    assert lines[2] == "STACKTRACE:"
    assert lines[3] == "# /app/a.py:1 in func_a"
    assert lines[4] == "# /app/b.py:2 in func_b"
    assert lines[5] == "*/"


def test_format_preserves_frame_order():
    """Test that frames are formatted in the order provided."""
    frames = [
        StackFrame(path="/third.py", line=3, name="third"),
        StackFrame(path="/first.py", line=1, name="first"),
        StackFrame(path="/second.py", line=2, name="second"),
    ]

    result = format_stacktrace_comment(frames)

    # Find positions of each frame in the output
    pos_third = result.index("third.py")
    pos_first = result.index("first.py")
    pos_second = result.index("second.py")

    # Verify order is preserved
    assert pos_third < pos_first < pos_second


def test_format_with_large_line_numbers():
    """Test formatting with large line numbers."""
    frames = [StackFrame(path="/app/big_file.py", line=999999, name="deep_function")]

    result = format_stacktrace_comment(frames)

    assert "# /app/big_file.py:999999 in deep_function" in result


def test_format_with_long_function_names():
    """Test formatting with long function names."""
    long_name = "very_long_function_name_that_describes_exactly_what_it_does_in_detail"
    frames = [StackFrame(path="/app/code.py", line=1, name=long_name)]

    result = format_stacktrace_comment(frames)

    assert f"# /app/code.py:1 in {long_name}" in result


def test_format_with_windows_paths():
    """Test formatting with Windows-style paths."""
    frames = [StackFrame(path="C:\\Users\\dev\\project\\views.py", line=42, name="view")]

    result = format_stacktrace_comment(frames)

    # Windows paths should be preserved as-is
    assert "# C:\\Users\\dev\\project\\views.py:42 in view" in result


def test_format_comment_is_sql_safe():
    """Test that formatted comment is safe to embed in SQL."""
    frames = [StackFrame(path="/app/test.py", line=1, name="test")]

    result = format_stacktrace_comment(frames)

    # Should not contain SQL injection patterns
    assert ";" not in result
    assert "--" not in result.replace("# ", "")  # Allow -- in comment markers
    assert "'" not in result
    assert '"' not in result

    # Should be a valid SQL comment block
    assert result.startswith("\n/*")
    assert result.endswith("*/")

import traceback

from sql_traceback.config import (
    MAX_STACK_FRAMES,
    MIN_APP_FRAMES,
    TRACEBACK_ENABLED,
)
from sql_traceback.filter import sanitize_filename, should_include_frame
from sql_traceback.traceback_info import StackFrame


def _is_stacktrace_enabled() -> bool:
    """Check if stacktrace is enabled via Django settings."""
    return bool(TRACEBACK_ENABLED)


def extract_stack_frames() -> list[StackFrame]:
    """Extract and filter stack frames from the current call stack.

    This function extracts the current stack trace and filters it to show
    only relevant application frames, excluding framework and library code.

    Returns:
        A list of StackFrame objects representing the filtered call stack.
    """
    try:
        # Get the current stacktrace
        stack = traceback.extract_stack()

        # Filter out framework and library calls to focus on application code
        filtered_stack = [frame for frame in stack if should_include_frame(frame)]

        # Build list of StackFrame objects
        frames = []

        # Use configurable number of most recent frames for better context
        if filtered_stack and len(filtered_stack) >= MIN_APP_FRAMES:
            for frame in filtered_stack[-MAX_STACK_FRAMES:]:
                safe_filename = sanitize_filename(frame.filename)
                frames.append(StackFrame(path=safe_filename, line=frame.lineno, name=frame.name))
        else:
            # If insufficient application frames found, include remaining frames
            for frame in stack[-min(3, len(stack)) :]:
                safe_filename = sanitize_filename(frame.filename)
                frames.append(StackFrame(path=safe_filename, line=frame.lineno, name=frame.name))

        return frames
    except Exception:
        # If stacktrace extraction fails, return empty list
        return []


def add_stacktrace_to_query(sql: str) -> tuple[str, list[StackFrame]]:
    """Add the current Python stacktrace to a SQL query as a comment.

    Args:
        sql: The original SQL query string

    Returns:
        A tuple of (modified_sql, frames) where:
        - modified_sql is the SQL query with a stacktrace comment appended
        - frames is a list of StackFrame objects representing the call stack

        If stacktracing is disabled or already present, returns (original_sql, []).
    """
    # Early return if disabled or already has stacktrace
    if not _is_stacktrace_enabled() or "/*\nSTACKTRACE:" in sql:
        return sql, []

    # Extract stack frames
    frames = extract_stack_frames()

    # If no frames were extracted, return original SQL
    if not frames:
        return sql, []

    # Format the stacktrace into a SQL comment
    stacktrace_lines = []
    for frame in frames:
        stacktrace_lines.append(f"# {frame.path}:{frame.line} in {frame.name}")

    stacktrace_comment = "\n".join(stacktrace_lines)

    # Append the stacktrace comment to the SQL query
    modified_sql = f"{sql}\n/*\nSTACKTRACE:\n{stacktrace_comment}\n*/"

    return modified_sql, frames

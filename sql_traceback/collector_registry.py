"""Thread-local registry for active TracebackCollector instances.

This module provides a clean separation between collector storage and
the context manager logic, eliminating circular imports.
"""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sql_traceback.traceback_info import TracebackCollector


__all__ = ["get_active_collector", "push_collector", "pop_collector"]


# Thread-local storage for active collector stack
_thread_local = threading.local()


def get_active_collector() -> "TracebackCollector | None":
    """Get the currently active TracebackCollector for this thread.

    Returns:
        The active TracebackCollector, or None if no context is active.
    """
    stack = getattr(_thread_local, "collector_stack", [])
    return stack[-1] if stack else None


def push_collector(collector: "TracebackCollector") -> None:
    """Push a new collector onto the stack for this thread.

    Args:
        collector: The TracebackCollector to push onto the stack.
    """
    if not hasattr(_thread_local, "collector_stack"):
        _thread_local.collector_stack = []
    _thread_local.collector_stack.append(collector)


def pop_collector() -> None:
    """Pop the current collector from the stack for this thread."""
    if hasattr(_thread_local, "collector_stack") and _thread_local.collector_stack:
        _thread_local.collector_stack.pop()

"""Data structures for programmatic access to traceback information.

This module provides classes for accessing stack frame information from SQL queries
in a structured way.
"""

from dataclasses import dataclass

__all__ = ["StackFrame", "QueryInfo", "TracebackCollector"]


@dataclass
class StackFrame:
    """Represents a single stack frame from a Python traceback.

    Attributes:
        path: The file path of the stack frame
        line: The line number in the file
        name: The function or method name
    """

    path: str
    line: int
    name: str


@dataclass
class QueryInfo:
    """Represents a SQL query with its associated stack frames.

    Attributes:
        sql: The SQL query string (with traceback comment)
        frames: List of stack frames that led to this query
    """

    sql: str
    frames: list[StackFrame]


class TracebackCollector:
    """Collects SQL queries and their associated stack frame information.

    This class is used by the sql_traceback context manager to store information
    about SQL queries executed within the context.

    Attributes:
        queries: List of QueryInfo objects representing all executed queries
    """

    def __init__(self) -> None:
        """Initialize an empty collector."""
        self.queries: list[QueryInfo] = []

    def add_query(self, sql: str, frames: list[StackFrame]) -> None:
        """Add a query and its stack frames to the collector.

        Args:
            sql: The SQL query string (with traceback comment)
            frames: List of stack frames that led to this query
        """
        self.queries.append(QueryInfo(sql=sql, frames=frames))

    @property
    def frames(self) -> list[StackFrame]:
        """Get the stack frames from the most recent query.

        This is a convenience property for accessing frames from the last query.

        Returns:
            List of stack frames from the most recent query, or an empty list
            if no queries have been executed.
        """
        if not self.queries:
            return []
        return self.queries[-1].frames

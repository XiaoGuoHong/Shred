from __future__ import annotations


class UndoWindowExpired(RuntimeError):
    """Raised when undo is attempted after the 10-second grace window."""


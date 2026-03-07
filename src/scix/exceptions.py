"""Custom exceptions for scix."""


class ScixError(RuntimeError):
    """Base error for scix operations."""


class CheckFailedError(ScixError):
    """Raised when a --check operation finds stale or missing output."""

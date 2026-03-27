"""Error hierarchy for user-facing and runtime failures."""

from __future__ import annotations


class BiggError(Exception):
    """Base exception for bigg-cli."""


class ConfigError(BiggError):
    """Raised when configuration is invalid."""


class UsageError(BiggError):
    """Raised for command usage and validation errors."""


class ApiError(BiggError):
    """Raised when upstream API interactions fail."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

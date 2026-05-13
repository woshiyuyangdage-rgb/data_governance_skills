"""Exceptions for the local governance tool registry."""


class ToolRegistryError(Exception):
    """Raised when the tool registry is missing or invalid."""


class ToolNotFoundError(Exception):
    """Raised when one configured or requested tool cannot be found."""

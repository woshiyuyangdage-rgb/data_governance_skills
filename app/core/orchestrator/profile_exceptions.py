"""Exceptions for workflow profile loading and routing."""


class WorkflowProfileError(Exception):
    """Base exception for workflow profile issues."""


class WorkflowProfileConfigError(WorkflowProfileError):
    """Raised when workflow profile configuration is invalid or missing."""


class WorkflowProfileNotFoundError(WorkflowProfileError):
    """Raised when a requested workflow profile does not exist."""

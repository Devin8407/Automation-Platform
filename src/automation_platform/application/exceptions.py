"""Exceptions raised by application use cases."""


class ApplicationError(Exception):
    """Base exception for application-layer errors."""

    pass


class InvalidWorkflowDefinitionError(ApplicationError):
    """Raised when a workflow definition is invalid."""

    pass


class WorkflowDefinitionNotFoundError(ApplicationError):
    """Raised when a requested workflow definition does not exist."""

    pass


class WorkflowDefinitionDisabledError(ApplicationError):
    """Raised when an operation requires an enabled workflow definition."""

    pass

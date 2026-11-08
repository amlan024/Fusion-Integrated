"""Domain exceptions for Employee Leave Management."""


class ElmDomainError(Exception):
    """Base exception for ELM business-rule violations."""


class InvalidLeaveTypeError(ElmDomainError):
    """Raised when an unsupported leave category is supplied."""


class InvalidLeaveTransitionError(ElmDomainError):
    """Raised when a leave request transition is not permitted."""


class InsufficientLeaveBalanceError(ElmDomainError):
    """Raised when the available balance is insufficient."""


class LeaveOverlapError(ElmDomainError):
    """Raised when a leave request overlaps another leave request."""


class UnauthorizedLeaveActionError(ElmDomainError):
    """Raised when an actor cannot perform a leave operation."""

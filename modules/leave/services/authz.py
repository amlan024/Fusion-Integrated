"""Shared permission checks for Employee Leave Management."""

from core.api.exceptions import PermissionDeniedError


def require_permission(actor, permission: str) -> None:
    """Reject unauthenticated actors and actors without the required grant."""
    if actor is None or not getattr(actor, "is_authenticated", True):
        raise PermissionDeniedError(
            "Authentication is required.",
            code="not_authenticated",
        )

    check = getattr(actor, "has_permission", None)
    if not callable(check) or not check(permission):
        raise PermissionDeniedError(
            f"This action requires {permission}.",
            code="permission_denied",
        )


def require_user_id(actor) -> int:
    """Return the IAM user ID, rejecting principals without an institute user."""
    user_id = getattr(actor, "user_id", None)
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise PermissionDeniedError(
            "An institute user identity is required.",
            code="permission_denied",
        )
    return user_id

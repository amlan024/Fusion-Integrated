"""Review and final-decision operations for leave applications."""

from django.db import transaction

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from modules.leave.models import LeaveApplication, LeaveDecision
from modules.leave.services.authz import require_permission, require_user_id

DIRECT_DECISION_CATEGORIES = {"CL", "RH"}
RECOMMENDATION_CATEGORIES = {"SCL", "EL", "COL", "VL"}
FINAL_DECISIONS = {"approved", "rejected"}


def _actor_role(actor) -> str:
    """Return the active IAM role used for the audit record."""
    role = getattr(actor, "active_role", None)
    if not isinstance(role, str) or not role.strip():
        raise BadRequestError("An active IAM role is required.")
    return role.strip()


def _validate_comments(comments: str) -> str:
    """Validate and normalize optional audit comments."""
    if not isinstance(comments, str):
        raise BadRequestError("Comments must be text.")
    return comments.strip()


@transaction.atomic
def recommend_application(
    *, actor, application_id: int, recommendation: str, comments: str = ""
) -> LeaveDecision:
    """Record an intermediate recommendation for a non-direct leave category."""
    require_permission(actor, "leave.application.review")
    actor_id = require_user_id(actor)
    actor_role = _actor_role(actor)
    comments = _validate_comments(comments)

    if recommendation not in {"recommended", "not_recommended"}:
        raise BadRequestError(
            "Recommendation must be 'recommended' or 'not_recommended'."
        )

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id)
        .first()
    )
    if application is None:
        raise NotFoundError("Leave application not found.")

    if application.user_id == actor_id:
        raise ConflictError("You cannot review your own leave application.")

    if application.status != "pending":
        raise ConflictError("Only pending applications can be reviewed.")

    if application.category not in RECOMMENDATION_CATEGORIES:
        raise ConflictError(
            "This leave category follows the direct-decision workflow."
        )

    if application.decisions.exists():
        raise ConflictError(
            "A recommendation or decision has already been recorded."
        )

    return LeaveDecision.objects.create(
        application=application,
        actor_user_id=actor_id,
        actor_role=actor_role,
        decision=recommendation,
        comments=comments,
    )


@transaction.atomic
def decide_application(
    *, actor, application_id: int, decision: str, comments: str = ""
) -> LeaveDecision:
    """Record the final approval or rejection of a pending application."""
    require_permission(actor, "leave.application.decide")
    actor_id = require_user_id(actor)
    actor_role = _actor_role(actor)
    comments = _validate_comments(comments)

    if decision not in FINAL_DECISIONS:
        raise BadRequestError("Decision must be 'approved' or 'rejected'.")

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id)
        .first()
    )
    if application is None:
        raise NotFoundError("Leave application not found.")

    if application.user_id == actor_id:
        raise ConflictError("You cannot decide your own leave application.")

    if application.status != "pending":
        raise ConflictError("Only pending applications can receive a decision.")

    prior_decisions = application.decisions.all()

    if prior_decisions.filter(decision__in=FINAL_DECISIONS).exists():
        raise ConflictError("A final decision has already been recorded.")

    if application.category in RECOMMENDATION_CATEGORIES:
        recommendation = prior_decisions.filter(
            decision__in=("recommended", "not_recommended")
        ).first()

        if recommendation is None:
            raise ConflictError(
                "A Unit Head recommendation must be recorded first."
            )

        if recommendation.actor_user_id == actor_id:
            raise ConflictError(
                "The person making the recommendation cannot make the final decision."
            )
    elif application.category not in DIRECT_DECISION_CATEGORIES:
        raise ConflictError("Unsupported leave category.")

    audit_record = LeaveDecision.objects.create(
        application=application,
        actor_user_id=actor_id,
        actor_role=actor_role,
        decision=decision,
        comments=comments,
    )

    application.status = decision
    application.save(update_fields=["status", "updated_at"])

    return audit_record

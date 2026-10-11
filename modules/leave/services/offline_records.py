
"""Administrative recording of leave sanctioned outside the system."""

from datetime import date

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.overlap import check_leave_overlap
from modules.leave.models import LeaveApplication, LeaveDecision
from modules.leave.services.authz import require_permission, require_user_id


def _actor_role(actor) -> str:
    """Return the active role used for audit records."""
    role = getattr(actor, "active_role", None)
    if not isinstance(role, str) or not role.strip():
        raise BadRequestError("An active IAM role is required.")
    return role.strip()


@transaction.atomic
def record_offline_leave(
    *,
    actor,
    employee_user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    reason: str,
    evidence_reference: str,
    comments: str = "",
    half_day: str = "",
    station_leave: bool = False,
) -> LeaveApplication:
    """Record an already-sanctioned offline leave with an audit trail."""
    require_permission(actor, "leave.record.manage")
    actor_id = require_user_id(actor)
    actor_role = _actor_role(actor)

    if (
        not isinstance(employee_user_id, int)
        or isinstance(employee_user_id, bool)
        or employee_user_id <= 0
    ):
        raise BadRequestError("A valid employee user ID is required.")

    if employee_user_id == actor_id:
        raise ConflictError("You cannot record your own leave as an administrator.")

    if category not in dict(LeaveApplication.CATEGORY_CHOICES):
        raise BadRequestError("Invalid leave category.")

    if (
        not isinstance(start_date, date)
        or isinstance(start_date, type(None))
        or not isinstance(end_date, date)
    ):
        raise BadRequestError("Start date and end date must be dates.")

    if start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    if not isinstance(reason, str) or not reason.strip():
        raise BadRequestError("A reason for leave is required.")

    if not isinstance(evidence_reference, str) or not evidence_reference.strip():
        raise BadRequestError("Evidence reference is required.")

    if not isinstance(comments, str):
        raise BadRequestError("Comments must be text.")

    if not isinstance(station_leave, bool):
        raise BadRequestError("Station leave must be a Boolean value.")

    if half_day not in ("", "first_half", "second_half"):
        raise BadRequestError("Invalid half-day selection.")

    if half_day and (category != "CL" or start_date != end_date):
        raise BadRequestError(
            "Half-day leave is allowed only for single-day CL."
        )

    existing = list(
        LeaveApplication.objects.select_for_update()
        .filter(
            user_id=employee_user_id,
            status__in=("pending", "approved"),
        )
        .values("start_date", "end_date", "category", "half_day", "status")
    )

    candidate = {
        "start_date": start_date,
        "end_date": end_date,
        "category": category,
        "half_day": half_day or None,
    }

    for request in existing:
        if not request["half_day"]:
            request["half_day"] = None

    if check_leave_overlap(candidate, existing):
        raise ConflictError(
            "The dates overlap another pending or approved leave."
        )

    application = LeaveApplication.objects.create(
        user_id=employee_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reason=reason.strip(),
        half_day=half_day,
        station_leave=station_leave,
        status="approved",
        offline_recorded=True,
        evidence_reference=evidence_reference.strip(),
        offline_recorded_by=actor_id,
    )

    LeaveDecision.objects.create(
        application=application,
        actor_user_id=actor_id,
        actor_role=actor_role,
        decision="approved",
        comments=comments.strip(),
    )

    return application

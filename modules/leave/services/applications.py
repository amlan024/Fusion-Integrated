"""Application operations for Employee Leave Management."""

from datetime import date

from django.db import transaction

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from modules.leave.domain.overlap import check_leave_overlap
from modules.leave.models import LeaveApplication
from modules.leave.services.authz import require_permission, require_user_id


@transaction.atomic
def create_application(
    *,
    actor,
    category: str,
    start_date: date,
    end_date: date,
    reason: str,
    half_day: str = "",
    station_leave: bool = False,
) -> LeaveApplication:
    """Create a pending application after basic validation and overlap checks."""
    require_permission(actor, "leave.application.create")
    user_id = require_user_id(actor)

    if category not in dict(LeaveApplication.CATEGORY_CHOICES):
        raise BadRequestError("Invalid leave category.")

    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise BadRequestError("Start date and end date must be dates.")

    if start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    if not isinstance(reason, str) or not reason.strip():
        raise BadRequestError("A reason for leave is required.")

    if half_day not in ("", "first_half", "second_half"):
        raise BadRequestError("Invalid half-day selection.")

    if half_day and (category != "CL" or start_date != end_date):
        raise BadRequestError(
            "Half-day leave is allowed only for single-day CL."
        )

    existing = list(
        LeaveApplication.objects.filter(
            user_id=user_id,
            status__in=("pending", "approved"),
        ).values(
            "start_date",
            "end_date",
            "category",
            "half_day",
            "status",
        )
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
            "The requested dates overlap another pending or approved leave."
        )

    return LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        reason=reason.strip(),
        station_leave=station_leave,
        status="pending",
    )


def list_own_applications(*, actor):
    """Return only the authenticated employee's applications."""
    require_permission(actor, "leave.application.view_self")
    user_id = require_user_id(actor)

    return LeaveApplication.objects.filter(user_id=user_id).order_by(
        "-created_at"
    )


@transaction.atomic
def withdraw_application(*, actor, application_id: int) -> LeaveApplication:
    """Withdraw an employee's own pending application."""
    require_permission(actor, "leave.application.withdraw")
    user_id = require_user_id(actor)

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id, user_id=user_id)
        .first()
    )

    if application is None:
        raise NotFoundError("Leave application not found.")

    if application.status != "pending":
        raise ConflictError("Only pending applications can be withdrawn.")

    application.status = "withdrawn"
    application.save(update_fields=["status", "updated_at"])
    return application

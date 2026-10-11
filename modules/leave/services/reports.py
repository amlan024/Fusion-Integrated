"""Administrative leave reports with optional filters."""

from datetime import date, datetime

from core.api.exceptions import BadRequestError
from modules.leave.models import LeaveApplication
from modules.leave.services.authz import require_permission, require_user_id


def list_leave_report(
    *,
    actor,
    employee_user_id=None,
    category=None,
    status=None,
    start_date=None,
    end_date=None,
):
    """Return authorized leave records matching the supplied filters."""
    require_permission(actor, "leave.report.view")
    require_user_id(actor)

    valid_categories = {value for value, _ in LeaveApplication.CATEGORY_CHOICES}
    valid_statuses = {value for value, _ in LeaveApplication.STATUS_CHOICES}

    if employee_user_id is not None and (
        not isinstance(employee_user_id, int)
        or isinstance(employee_user_id, bool)
        or employee_user_id <= 0
    ):
        raise BadRequestError("Employee user ID must be a positive integer.")

    if category is not None and category not in valid_categories:
        raise BadRequestError("Invalid leave category.")

    if status is not None and status not in valid_statuses:
        raise BadRequestError("Invalid leave status.")

    for field_name, value in (
        ("Start date", start_date),
        ("End date", end_date),
    ):
        if value is not None and (
            not isinstance(value, date) or isinstance(value, datetime)
        ):
            raise BadRequestError(f"{field_name} must be a date.")

    if start_date and end_date and start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    records = LeaveApplication.objects.all()

    if employee_user_id is not None:
        records = records.filter(user_id=employee_user_id)

    if category is not None:
        records = records.filter(category=category)

    if status is not None:
        records = records.filter(status=status)

    # Include leave that overlaps the requested date range.
    if start_date is not None:
        records = records.filter(end_date__gte=start_date)

    if end_date is not None:
        records = records.filter(start_date__lte=end_date)

    return records.order_by("start_date", "user_id", "id")

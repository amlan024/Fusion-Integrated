
from datetime import date, datetime

CATEGORIES = {"CL", "RH", "SCL", "EL", "COL", "VL"}
STATUSES = {"pending", "approved", "rejected", "withdrawn", "cancelled"}
HALF_DAYS = {"first_half", "second_half"}


def _validate_request(request, require_status=False):
    """Validate a leave request dictionary."""
    if not isinstance(request, dict):
        raise TypeError("Each request must be a dictionary.")

    required = {"start_date", "end_date", "category"}
    if require_status:
        required.add("status")

    if not required.issubset(request):
        raise ValueError("Request is missing required fields.")

    start = request["start_date"]
    end = request["end_date"]

    for value in (start, end):
        if isinstance(value, datetime) or not isinstance(value, date):
            raise TypeError("Dates must be datetime.date values, not datetime.datetime.")

    if start > end:
        raise ValueError("Start date cannot be after end date.")

    if request["category"] not in CATEGORIES:
        raise ValueError("Invalid leave category.")

    if require_status and request["status"] not in STATUSES:
        raise ValueError("Invalid leave status.")

    half_day = request.get("half_day")
    if half_day is not None:
        if not isinstance(half_day, str) or half_day not in HALF_DAYS:
            raise ValueError("Invalid half_day value.")
        if request["category"] != "CL":
            raise ValueError("Half-day leave is allowed only for CL.")
        if start != end:
            raise ValueError("Half-day CL must cover exactly one date.")


def check_leave_overlap(new_request, existing_requests):
    """
    Return original pending/approved requests that overlap the new request.

    Opposite half-day CL requests on the same single date do not conflict.
    Inputs are validated before conflicts are checked and are never mutated.
    """
    _validate_request(new_request)

    if not isinstance(existing_requests, list):
        raise TypeError("Existing requests must be a list.")

    # Validate every request, including terminal-status requests, first.
    for request in existing_requests:
        _validate_request(request, require_status=True)

    conflicts = []
    new_start = new_request["start_date"]
    new_end = new_request["end_date"]

    for request in existing_requests:
        if request["status"] not in {"pending", "approved"}:
            continue

        existing_start = request["start_date"]
        existing_end = request["end_date"]

        # Inclusive date-range overlap.
        overlaps = new_start <= existing_end and existing_start <= new_end
        if not overlaps:
            continue

        # Opposite half-days on the same single date are compatible.
        same_single_date = (
            new_start == new_end == existing_start == existing_end
        )
        new_half = new_request.get("half_day")
        existing_half = request.get("half_day")

        opposite_half_days = (
            new_request["category"] == "CL"
            and request["category"] == "CL"
            and same_single_date
            and new_half is not None
            and existing_half is not None
            and new_half != existing_half
        )

        if opposite_half_days:
            continue

        conflicts.append(request)

    return conflicts

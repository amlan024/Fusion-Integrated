
"""Pure ELM leave calculations.

No Django imports, database access, or policy configuration.
Policy-dependent choices are passed explicitly by the caller.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"

LEAVE_CATEGORIES = frozenset({CL, RH, SCL, EL, COL, VL})
CONTINUOUS_CALENDAR_CATEGORIES = frozenset({EL, COL, VL})


class LeaveCalculationError(ValueError):
    """Invalid leave calculation input."""


def _date_range(start: date, end: date):
    if not isinstance(start, date) or not isinstance(end, date):
        raise LeaveCalculationError("Start and end must be dates.")
    if end < start:
        raise LeaveCalculationError("End date cannot precede start date.")

    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def count_leave_days(
    category: str,
    start: date,
    end: date,
    *,
    count_calendar_days: bool,
    holidays: Iterable[date] = (),
) -> Decimal:
    """Count leave days using an explicit counting policy.

    EL, COL and VL normally use continuous calendar-day counting.
    The caller must select the applicable policy for other categories.
    """
    if category not in LEAVE_CATEGORIES:
        raise LeaveCalculationError(f"Unsupported leave category: {category}")

    if category in CONTINUOUS_CALENDAR_CATEGORIES and not count_calendar_days:
        raise LeaveCalculationError(
            f"{category} requires continuous calendar-day counting."
        )

    holiday_dates = set(holidays)

    if count_calendar_days:
        return Decimal(sum(1 for _ in _date_range(start, end)))

    return Decimal(
        sum(
            1
            for day in _date_range(start, end)
            if day.weekday() < 5 and day not in holiday_dates
        )
    )


def half_day_cl_amount(half: str) -> Decimal:
    """Return the CL deduction for a first-half or second-half request."""
    if half not in {"first", "second"}:
        raise LeaveCalculationError(
            "Half-day CL must be either 'first' or 'second'."
        )
    return Decimal("0.5")


def validate_half_day_cl_date(
    start: date,
    end: date,
    half: str,
) -> Decimal:
    """Validate that a half-day CL request covers exactly one date."""
    if start != end:
        raise LeaveCalculationError(
            "A half-day CL request must cover exactly one date."
        )
    return half_day_cl_amount(half)


def half_day_cl_requests_overlap(
    first_date: date,
    first_half: str,
    second_date: date,
    second_half: str,
) -> bool:
    """Different halves on one date do not overlap."""
    if first_date != second_date:
        return False
    if first_half not in {"first", "second"}:
        raise LeaveCalculationError("Invalid first CL half.")
    if second_half not in {"first", "second"}:
        raise LeaveCalculationError("Invalid second CL half.")
    return first_half == second_half


def periods_overlap(
    first_start: date,
    first_end: date,
    second_start: date,
    second_end: date,
) -> bool:
    """Inclusive date-period overlap."""
    if first_end < first_start or second_end < second_start:
        raise LeaveCalculationError("Invalid date period.")
    return first_start <= second_end and second_start <= first_end


def faculty_vl_to_el(unused_vl: Decimal | int | str) -> Decimal:
    """Convert unused faculty VL to EL at the specified 2:1 ratio.

    Fractional conversion is retained.
    """
    try:
        amount = Decimal(str(unused_vl))
    except Exception as exc:
        raise LeaveCalculationError("Invalid VL balance.") from exc

    if not amount.is_finite() or amount < 0:
        raise LeaveCalculationError("VL balance cannot be negative.")

    return amount / Decimal("2")


def remaining_balance(
    opening_balance: Decimal | int | str,
    credited: Decimal | int | str,
    consumed: Decimal | int | str,
) -> Decimal:
    """Calculate a balance without allowing a negative result."""
    opening = Decimal(str(opening_balance))
    credit = Decimal(str(credited))
    used = Decimal(str(consumed))

    if min(opening, credit, used) < 0:
        raise LeaveCalculationError("Balance values cannot be negative.")

    result = opening + credit - used
    if result < 0:
        raise LeaveCalculationError("Insufficient leave balance.")

    return result


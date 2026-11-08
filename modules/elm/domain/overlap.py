"""Date-overlap validation for leave requests."""

from dataclasses import dataclass
from datetime import date

from modules.elm.domain.exceptions import LeaveOverlapError


@dataclass(frozen=True)
class LeavePeriod:
    start_date: date
    end_date: date
    half_day: bool = False

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("Start date cannot be after end date.")

        if self.half_day and self.start_date != self.end_date:
            raise ValueError("A half-day period must cover one date.")


def periods_overlap(first: LeavePeriod, second: LeavePeriod) -> bool:
    """Check whether two leave periods share at least one calendar date."""
    return (
        first.start_date <= second.end_date
        and second.start_date <= first.end_date
    )


def validate_no_overlap(
    requested: LeavePeriod,
    existing_periods: list[LeavePeriod],
) -> None:
    """Reject overlapping periods.

    Half-day CL exceptions must be evaluated by the applicable ELM rule
    before being allowed; this function does not assume an exception.
    """
    for existing in existing_periods:
        if periods_overlap(requested, existing):
            raise LeaveOverlapError(
                "The requested leave overlaps an existing leave period."
            )

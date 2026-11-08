"""Domain representation and validation of an ELM leave request."""

from dataclasses import dataclass
from datetime import date

from modules.elm.domain.exceptions import (
    ElmDomainError,
    InvalidLeaveTypeError,
)
from modules.elm.domain.leave_types import (
    CL,
    LEAVE_TYPE_CODES,
)


@dataclass(frozen=True)
class LeaveRequest:
    applicant_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    half_day: bool = False
    substitute_id: int | None = None

    def __post_init__(self):
        if self.applicant_id <= 0:
            raise ElmDomainError("A valid applicant is required.")

        if self.leave_type not in LEAVE_TYPE_CODES:
            raise InvalidLeaveTypeError(
                f"Unsupported leave type: {self.leave_type}"
            )

        if self.start_date > self.end_date:
            raise ElmDomainError(
                "Leave start date cannot be after its end date."
            )

        if self.half_day and self.leave_type != CL:
            raise ElmDomainError(
                "Half-day leave is permitted only for Casual Leave."
            )

        if self.half_day and self.start_date != self.end_date:
            raise ElmDomainError(
                "Half-day leave must cover a single date."
            )

        if not self.reason or not self.reason.strip():
            raise ElmDomainError("A leave reason is required.")

        if self.substitute_id == self.applicant_id:
            raise ElmDomainError(
                "An applicant cannot nominate themselves as substitute."
            )

    @property
    def total_calendar_days(self) -> int:
        """Count both the start and end dates."""
        return (self.end_date - self.start_date).days + 1

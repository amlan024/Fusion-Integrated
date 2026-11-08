"""Leave balance calculations using Decimal precision."""

from decimal import Decimal

from modules.elm.domain.exceptions import InsufficientLeaveBalanceError


def requested_leave_units(
    calendar_days: int,
    half_day: bool = False,
) -> Decimal:
    """Calculate the leave units requested.

    Continuous leave counts calendar days, including intervening
    weekends and holidays. A half-day request consumes 0.5 units.
    """
    if calendar_days <= 0:
        raise ValueError("Calendar days must be greater than zero.")

    if half_day:
        if calendar_days != 1:
            raise ValueError("Half-day leave must cover one calendar day.")
        return Decimal("0.5")

    return Decimal(calendar_days)


def validate_sufficient_balance(
    available_balance: Decimal,
    requested_units: Decimal,
) -> None:
    """Raise an error if the available balance is insufficient."""
    if available_balance < Decimal("0"):
        raise ValueError("Available balance cannot be negative.")

    if requested_units <= Decimal("0"):
        raise ValueError("Requested leave units must be positive.")

    if available_balance < requested_units:
        raise InsufficientLeaveBalanceError(
            f"Insufficient leave balance: available {available_balance}, "
            f"requested {requested_units}."
        )


def remaining_balance(
    available_balance: Decimal,
    approved_units: Decimal,
) -> Decimal:
    """Return the balance after an approved leave deduction."""
    validate_sufficient_balance(available_balance, approved_units)
    return available_balance - approved_units

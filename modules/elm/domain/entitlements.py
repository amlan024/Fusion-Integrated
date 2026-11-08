
"""Leave entitlement and carry-forward calculations."""

from decimal import Decimal, InvalidOperation

from modules.elm.domain.exceptions import ElmDomainError


def to_decimal(value) -> Decimal:
    """Convert a numeric value to Decimal safely."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ElmDomainError("Invalid leave entitlement value.")

    if not result.is_finite() or result < Decimal("0"):
        raise ElmDomainError(
            "Leave entitlement values must be finite and non-negative."
        )

    return result


def calculate_vl_to_el_conversion(vl_balance) -> Decimal:
    """Convert Vacation Leave to Earned Leave at 2 VL : 1 EL.

    Fractions are preserved; no integer rounding is applied.
    """
    vacation_leave = to_decimal(vl_balance)
    return vacation_leave / Decimal("2")


def calculate_carry_forward(
    unused_balance,
    carry_forward_limit,
) -> Decimal:
    """Calculate the amount eligible for carry-forward.

    The applicable limit is supplied by the current configured policy.
    """
    unused = to_decimal(unused_balance)
    limit = to_decimal(carry_forward_limit)

    return min(unused, limit)


def calculate_lapsed_balance(
    unused_balance,
    carry_forward_amount,
) -> Decimal:
    """Calculate unused balance that lapses after carry-forward."""
    unused = to_decimal(unused_balance)
    carried = to_decimal(carry_forward_amount)

    if carried > unused:
        raise ElmDomainError(
            "Carry-forward cannot exceed the unused leave balance."
        )

    return unused - carried


def calculate_updated_balance(
    current_balance,
    credited_units,
    deducted_units,
) -> Decimal:
    """Calculate a balance after credits and deductions."""
    current = to_decimal(current_balance)
    credited = to_decimal(credited_units)
    deducted = to_decimal(deducted_units)

    updated = current + credited - deducted

    if updated < Decimal("0"):
        raise ElmDomainError(
            "The transaction would make the leave balance negative."
        )

    return updated


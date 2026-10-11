"""Application services for leave entitlement calculations."""

from modules.leave.domain.entitlements import annual_entitlement
from modules.leave.models import LeavePolicy


def get_annual_entitlement(
    *,
    category: str,
    is_faculty: bool,
    col_eligible: bool = False,
) -> float:
    """Calculate annual entitlement using the current policy or defaults."""
    policy = LeavePolicy.objects.filter(category=category).first()

    return annual_entitlement(
        category=category,
        is_faculty=is_faculty,
        col_eligible=col_eligible,
        policy=policy,
    )

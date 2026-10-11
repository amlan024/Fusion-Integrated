
"""Pure domain rules for leave entitlements and year-end balances."""



DEFAULT_ENTITLEMENTS = {
    "CL": (8, 8),
    "RH": (2, 2),
    "SCL": (15, 15),
    "EL": (0, 30),
    "COL": (0, 20),
    "VL": (60, 0),
}


def annual_entitlement(
    category: str,
    is_faculty: bool,
    col_eligible: bool = False,
    *,
    policy=None,
) -> float:
    """Return entitlement using an optional policy or the default rules."""
    if category not in DEFAULT_ENTITLEMENTS:
        raise ValueError(f"Unknown leave category: {category}")

    if policy is not None:
        if policy.category != category:
            raise ValueError("Policy category does not match the requested category.")
        if not policy.enabled:
            return 0
        if category == "COL" and policy.requires_col_eligibility and not col_eligible:
            return 0

        value = (
            policy.faculty_entitlement
            if is_faculty
            else policy.staff_entitlement
        )
        return float(value)

    if category == "COL" and not col_eligible:
        return 0

    faculty_value, staff_value = DEFAULT_ENTITLEMENTS[category]
    return faculty_value if is_faculty else staff_value


def calculate_year_end_balances(
    balances: dict[str, float],
    is_faculty: bool,
) -> dict[str, float]:
    """Return updated leave balances after year-end processing."""
    if any(balance < 0 for balance in balances.values()):
        raise ValueError("Negative leave balance detected")

    updated_balances = balances.copy()

    # CL, RH and SCL lapse at year-end.
    for category in ("CL", "RH", "SCL"):
        if category in updated_balances:
            updated_balances[category] = 0

    # EL and COL carry forward unchanged.
    # Faculty's unused VL converts to EL at 2 VL : 1 EL.
    if is_faculty and "VL" in balances:
        updated_balances["EL"] = balances.get("EL", 0) + balances["VL"] / 2
        updated_balances["VL"] = 0

    return updated_balances

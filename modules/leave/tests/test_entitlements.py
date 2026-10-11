import pytest

from modules.leave.domain.entitlements import annual_entitlement, calculate_year_end_balances


def test_annual_entitlement():
    assert annual_entitlement('CL', False) == 8
    assert annual_entitlement('RH', False) == 2
    assert annual_entitlement('SCL', False) == 15
    assert annual_entitlement('CL', True) == 8
    assert annual_entitlement('RH', True) == 2
    assert annual_entitlement('SCL', True) == 15
    assert annual_entitlement('EL', False) == 30
    assert annual_entitlement('EL', True) == 0
    assert annual_entitlement('VL', True) == 60
    assert annual_entitlement('VL', False) == 0
    assert annual_entitlement('COL', False, True) == 20
    assert annual_entitlement('COL', False, False) == 0

def test_calculate_year_end_balances():
    original = {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "COL": 20, "other": 7}
    result = calculate_year_end_balances(original, False)
    assert result == {"CL": 0, "RH": 0, "SCL": 0, "EL": 30, "COL": 20, "other": 7}
    assert original == {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "COL": 20, "other": 7}

    assert calculate_year_end_balances({"VL": 5, "EL": 10}, True) == {"VL": 0, "EL": 12.5}
    assert calculate_year_end_balances({"VL": 1.5, "EL": 10}, True) == {"VL": 0, "EL": 10.75}
    assert calculate_year_end_balances({"VL": 5}, True) == {"VL": 0, "EL": 2.5}
    assert calculate_year_end_balances({"EL": 10}, True) == {"EL": 10}
    assert calculate_year_end_balances({"VL": 5, "EL": 10}, False) == {"VL": 5, "EL": 10}

    with pytest.raises(ValueError):
        calculate_year_end_balances({"CL": -5}, False)



def test_annual_entitlement_uses_custom_policy():
    from types import SimpleNamespace

    policy = SimpleNamespace(
        category="CL",
        faculty_entitlement=10,
        staff_entitlement=6,
        requires_col_eligibility=False,
        enabled=True,
    )

    assert annual_entitlement("CL", True, policy=policy) == 10
    assert annual_entitlement("CL", False, policy=policy) == 6


def test_disabled_policy_returns_zero_entitlement():
    from types import SimpleNamespace

    policy = SimpleNamespace(
        category="CL",
        faculty_entitlement=8,
        staff_entitlement=8,
        requires_col_eligibility=False,
        enabled=False,
    )

    assert annual_entitlement("CL", False, policy=policy) == 0


def test_custom_col_policy_respects_eligibility():
    from types import SimpleNamespace

    policy = SimpleNamespace(
        category="COL",
        faculty_entitlement=20,
        staff_entitlement=20,
        requires_col_eligibility=True,
        enabled=True,
    )

    assert annual_entitlement("COL", False, False, policy=policy) == 0
    assert annual_entitlement("COL", False, True, policy=policy) == 20


def test_policy_category_must_match_requested_category():
    from types import SimpleNamespace

    policy = SimpleNamespace(
        category="RH",
        faculty_entitlement=2,
        staff_entitlement=2,
        requires_col_eligibility=False,
        enabled=True,
    )

    import pytest

    with pytest.raises(ValueError, match="does not match"):
        annual_entitlement("CL", False, policy=policy)


from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.balance import (
    remaining_balance,
    requested_leave_units,
    validate_sufficient_balance,
)
from modules.elm.domain.entitlements import (
    calculate_carry_forward,
    calculate_lapsed_balance,
    calculate_updated_balance,
    calculate_vl_to_el_conversion,
)
from modules.elm.domain.exceptions import (
    ElmDomainError,
    InsufficientLeaveBalanceError,
    InvalidLeaveTransitionError,
    LeaveOverlapError,
)
from modules.elm.domain.leave_types import CL, EL, RH
from modules.elm.domain.overlap import (
    LeavePeriod,
    validate_no_overlap,
)
from modules.elm.domain.request import LeaveRequest
from modules.elm.domain.state_machine import (
    APPROVED,
    PENDING_SANCTION,
    PENDING_UNIT_HEAD,
    REJECTED,
    WITHDRAWN,
    allowed_actions,
    transition,
)


def test_supported_leave_request():
    request = LeaveRequest(
        applicant_id=1,
        leave_type=CL,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        reason="Personal work",
    )
    assert request.total_calendar_days == 2


def test_half_day_cl_request():
    request = LeaveRequest(
        applicant_id=1,
        leave_type=CL,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 10),
        reason="Personal work",
        half_day=True,
    )
    assert request.half_day is True


def test_half_day_non_cl_is_rejected():
    with pytest.raises(ElmDomainError):
        LeaveRequest(
            applicant_id=1,
            leave_type=EL,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 10),
            reason="Personal work",
            half_day=True,
        )


def test_inclusive_calendar_day_count():
    request = LeaveRequest(
        applicant_id=1,
        leave_type=EL,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        reason="Personal work",
    )
    assert request.total_calendar_days == 3


def test_unit_head_final_approval_for_cl():
    assert transition(PENDING_UNIT_HEAD, "unit_head_approve", CL) == APPROVED


def test_unit_head_final_approval_for_rh():
    assert transition(PENDING_UNIT_HEAD, "unit_head_approve", RH) == APPROVED


def test_unit_head_recommendation_routes_higher():
    assert (
        transition(PENDING_UNIT_HEAD, "unit_head_recommend", EL)
        == PENDING_SANCTION
    )


def test_unit_head_not_recommended_still_routes_higher():
    assert (
        transition(PENDING_UNIT_HEAD, "unit_head_not_recommend", EL)
        == PENDING_SANCTION
    )


def test_higher_sanction_rejection():
    assert transition(PENDING_SANCTION, "sanction_reject") == REJECTED


def test_unit_head_cannot_finally_approve_el():
    with pytest.raises(InvalidLeaveTransitionError):
        transition(PENDING_UNIT_HEAD, "unit_head_approve", EL)


def test_unit_head_requires_leave_category():
    with pytest.raises(InvalidLeaveTransitionError):
        transition(PENDING_UNIT_HEAD, "unit_head_approve")


def test_allowed_actions_for_higher_sanction_leave():
    actions = allowed_actions(PENDING_UNIT_HEAD, EL)
    assert "unit_head_recommend" in actions
    assert "unit_head_not_recommend" in actions
    assert "unit_head_approve" not in actions


def test_withdraw_pending_substitute_request():
    assert transition("pending_substitute", "withdraw") == WITHDRAWN


def test_full_day_overlap_is_rejected():
    requested = LeavePeriod(date(2026, 11, 10), date(2026, 11, 12))
    existing = [LeavePeriod(date(2026, 11, 12), date(2026, 11, 14))]

    with pytest.raises(LeaveOverlapError):
        validate_no_overlap(requested, existing)


def test_non_overlapping_periods_are_allowed():
    requested = LeavePeriod(date(2026, 11, 10), date(2026, 11, 11))
    existing = [LeavePeriod(date(2026, 11, 12), date(2026, 11, 14))]

    validate_no_overlap(requested, existing)


def test_half_day_consumes_half_unit():
    assert requested_leave_units(1, half_day=True) == Decimal("0.5")


def test_full_day_units():
    assert requested_leave_units(3) == Decimal("3")


def test_insufficient_balance_is_rejected():
    with pytest.raises(InsufficientLeaveBalanceError):
        validate_sufficient_balance(Decimal("2"), Decimal("3"))


def test_remaining_balance():
    assert remaining_balance(Decimal("10"), Decimal("3")) == Decimal("7")


def test_vl_to_el_conversion_preserves_fraction():
    assert calculate_vl_to_el_conversion(Decimal("5")) == Decimal("2.5")


def test_carry_forward_limit():
    assert calculate_carry_forward(Decimal("12"), Decimal("8")) == Decimal("8")


def test_lapsed_balance():
    assert calculate_lapsed_balance(Decimal("12"), Decimal("8")) == Decimal("4")


def test_updated_balance():
    result = calculate_updated_balance(
        Decimal("10"),
        Decimal("2"),
        Decimal("3"),
    )
    assert result == Decimal("9")


def test_negative_updated_balance_is_rejected():
    with pytest.raises(ElmDomainError):
        calculate_updated_balance(
            Decimal("2"),
            Decimal("0"),
            Decimal("3"),
        )


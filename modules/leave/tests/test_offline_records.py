"""Tests for retrospective offline leave recording."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    PermissionDeniedError,
)
from modules.leave.models import LeaveApplication, LeaveDecision
from modules.leave.services.offline_records import record_offline_leave

pytestmark = pytest.mark.django_db

RECORD_PERMISSION = {"leave.record.manage"}



def make_actor(user_id=900, permissions=None, active_role="Leave Administrator"):
    if permissions is None:
        permissions = RECORD_PERMISSION

    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        active_role=active_role,
        has_permission=lambda code: code in permissions,
    )



def record_leave(**overrides):
    arguments = {
        "actor": make_actor(),
        "employee_user_id": 101,
        "category": "CL",
        "start_date": date(2026, 11, 2),
        "end_date": date(2026, 11, 2),
        "reason": "Previously sanctioned leave",
        "evidence_reference": "SANCTION-2026-001",
        "comments": "Verified against offline sanction.",
    }
    arguments.update(overrides)
    return record_offline_leave(**arguments)


def test_records_approved_leave_with_audit_trail():
    application = record_leave()

    assert application.user_id == 101
    assert application.status == "approved"
    assert application.offline_recorded is True
    assert application.evidence_reference == "SANCTION-2026-001"
    assert application.offline_recorded_by == 900

    decision = LeaveDecision.objects.get(application=application)
    assert decision.actor_user_id == 900
    assert decision.actor_role == "Leave Administrator"
    assert decision.decision == "approved"


def test_recording_requires_permission():
    with pytest.raises(PermissionDeniedError):
        record_leave(actor=make_actor(permissions=set()))

    assert LeaveApplication.objects.count() == 0


def test_recording_requires_evidence_reference():
    with pytest.raises(BadRequestError, match="Evidence reference"):
        record_leave(evidence_reference="   ")

    assert LeaveApplication.objects.count() == 0


def test_recording_rejects_invalid_date_range():
    with pytest.raises(BadRequestError, match="Start date"):
        record_leave(
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 2),
        )

    assert LeaveApplication.objects.count() == 0


def test_recording_rejects_overlapping_active_leave():
    LeaveApplication.objects.create(
        user_id=101,
        category="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Existing leave",
        status="approved",
    )

    with pytest.raises(ConflictError, match="overlap"):
        record_leave(
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 4),
        )

    assert LeaveApplication.objects.count() == 1


def test_administrator_cannot_record_own_leave():
    with pytest.raises(ConflictError, match="own leave"):
        record_leave(
            actor=make_actor(user_id=101),
            employee_user_id=101,
        )

    assert LeaveApplication.objects.count() == 0

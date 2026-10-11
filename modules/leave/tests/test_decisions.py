"""Tests for leave recommendations and final decisions."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    PermissionDeniedError,
)
from modules.leave.models import LeaveApplication, LeaveDecision
from modules.leave.services import decisions

pytestmark = pytest.mark.django_db

REVIEW_PERMISSION = {"leave.application.review"}
DECIDE_PERMISSION = {"leave.application.decide"}


def make_actor(user_id, permissions, active_role="Unit Head"):
    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        active_role=active_role,
        has_permission=lambda code: code in permissions,
    )


def create_application(user_id=101, category="EL", status="pending"):
    return LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Personal work",
        status=status,
    )


def test_unauthorized_actor_cannot_recommend():
    application = create_application()
    actor = make_actor(202, set())

    with pytest.raises(PermissionDeniedError):
        decisions.recommend_application(
            actor=actor,
            application_id=application.pk,
            recommendation="recommended",
        )

    assert application.decisions.count() == 0


def test_recommendation_is_recorded_without_final_approval():
    application = create_application()
    actor = make_actor(202, REVIEW_PERMISSION)

    record = decisions.recommend_application(
        actor=actor,
        application_id=application.pk,
        recommendation="recommended",
        comments="Recommended by Unit Head",
    )

    application.refresh_from_db()
    assert record.decision == "recommended"
    assert record.actor_user_id == 202
    assert record.actor_role == "Unit Head"
    assert application.status == "pending"


def test_invalid_recommendation_is_rejected():
    application = create_application()
    actor = make_actor(202, REVIEW_PERMISSION)

    with pytest.raises(BadRequestError):
        decisions.recommend_application(
            actor=actor,
            application_id=application.pk,
            recommendation="approved",
        )


def test_direct_category_cannot_use_recommendation_workflow():
    application = create_application(category="CL")
    actor = make_actor(202, REVIEW_PERMISSION)

    with pytest.raises(ConflictError):
        decisions.recommend_application(
            actor=actor,
            application_id=application.pk,
            recommendation="recommended",
        )


def test_recommendation_cannot_be_recorded_twice():
    application = create_application()
    actor = make_actor(202, REVIEW_PERMISSION)

    decisions.recommend_application(
        actor=actor,
        application_id=application.pk,
        recommendation="recommended",
    )

    with pytest.raises(ConflictError):
        decisions.recommend_application(
            actor=actor,
            application_id=application.pk,
            recommendation="not_recommended",
        )


def test_indirect_category_requires_recommendation_before_decision():
    application = create_application(category="EL")
    actor = make_actor(202, DECIDE_PERMISSION, "Registrar")

    with pytest.raises(ConflictError):
        decisions.decide_application(
            actor=actor,
            application_id=application.pk,
            decision="approved",
        )

    application.refresh_from_db()
    assert application.status == "pending"


def test_direct_category_can_be_approved():
    application = create_application(category="CL")
    actor = make_actor(202, DECIDE_PERMISSION, "Unit Head")

    record = decisions.decide_application(
        actor=actor,
        application_id=application.pk,
        decision="approved",
    )

    application.refresh_from_db()
    assert record.decision == "approved"
    assert application.status == "approved"


def test_indirect_category_can_be_decided_after_recommendation():
    application = create_application(category="EL")

    decisions.recommend_application(
        actor=make_actor(202, REVIEW_PERMISSION, "Unit Head"),
        application_id=application.pk,
        recommendation="recommended",
    )

    record = decisions.decide_application(
        actor=make_actor(303, DECIDE_PERMISSION, "Registrar"),
        application_id=application.pk,
        decision="approved",
    )

    application.refresh_from_db()
    assert record.actor_user_id == 303
    assert application.status == "approved"
    assert application.decisions.count() == 2


def test_employee_cannot_decide_own_application():
    application = create_application(user_id=101)
    actor = make_actor(101, DECIDE_PERMISSION, "Registrar")

    with pytest.raises(ConflictError):
        decisions.decide_application(
            actor=actor,
            application_id=application.pk,
            decision="approved",
        )


def test_decision_requires_valid_value():
    application = create_application(category="CL")
    actor = make_actor(202, DECIDE_PERMISSION, "Unit Head")

    with pytest.raises(BadRequestError):
        decisions.decide_application(
            actor=actor,
            application_id=application.pk,
            decision="recommended",
        )


def test_final_decision_cannot_be_repeated():
    application = create_application(category="CL")
    actor = make_actor(202, DECIDE_PERMISSION, "Unit Head")

    decisions.decide_application(
        actor=actor,
        application_id=application.pk,
        decision="rejected",
    )

    with pytest.raises(ConflictError):
        decisions.decide_application(
            actor=actor,
            application_id=application.pk,
            decision="approved",
        )

    assert LeaveDecision.objects.filter(application=application).count() == 1

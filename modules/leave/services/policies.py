"""Administration of current leave policies."""

from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.models import LeaveApplication, LeavePolicy
from modules.leave.services.authz import require_permission, require_user_id

VALID_CATEGORIES = {
    category for category, _label in LeaveApplication.CATEGORY_CHOICES
}


def _validate_policy(
    *,
    category: str,
    faculty_entitlement,
    staff_entitlement,
    requires_col_eligibility: bool,
    counts_weekends: bool,
    counts_public_holidays: bool,
    carries_forward: bool,
    enabled: bool,
) -> tuple:
    """Validate and normalize policy values before persistence."""
    if category not in VALID_CATEGORIES:
        raise BadRequestError("Invalid leave category.")

    try:
        faculty_value = Decimal(str(faculty_entitlement))
        staff_value = Decimal(str(staff_entitlement))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BadRequestError("Entitlements must be valid numbers.") from exc

    if not faculty_value.is_finite() or not staff_value.is_finite():
        raise BadRequestError("Entitlements must be finite numbers.")

    if faculty_value < 0 or staff_value < 0:
        raise BadRequestError("Entitlements cannot be negative.")

    if (
        faculty_value.as_tuple().exponent < -2
        or staff_value.as_tuple().exponent < -2
    ):
        raise BadRequestError("Entitlements support at most two decimal places.")

    flags = (
        requires_col_eligibility,
        counts_weekends,
        counts_public_holidays,
        carries_forward,
        enabled,
    )
    if any(not isinstance(flag, bool) for flag in flags):
        raise BadRequestError("Policy flags must be Boolean values.")

    return (
        category,
        faculty_value,
        staff_value,
        requires_col_eligibility,
        counts_weekends,
        counts_public_holidays,
        carries_forward,
        enabled,
    )


@transaction.atomic
def create_policy(
    *,
    actor,
    category: str,
    faculty_entitlement=0,
    staff_entitlement=0,
    requires_col_eligibility: bool = False,
    counts_weekends: bool = False,
    counts_public_holidays: bool = False,
    carries_forward: bool = False,
    enabled: bool = True,
) -> LeavePolicy:
    """Create the current policy for a category."""
    require_permission(actor, "leave.policy.manage")
    require_user_id(actor)

    values = _validate_policy(
        category=category,
        faculty_entitlement=faculty_entitlement,
        staff_entitlement=staff_entitlement,
        requires_col_eligibility=requires_col_eligibility,
        counts_weekends=counts_weekends,
        counts_public_holidays=counts_public_holidays,
        carries_forward=carries_forward,
        enabled=enabled,
    )

    (
        category,
        faculty_value,
        staff_value,
        requires_col_eligibility,
        counts_weekends,
        counts_public_holidays,
        carries_forward,
        enabled,
    ) = values

    try:
        return LeavePolicy.objects.create(
            category=category,
            faculty_entitlement=faculty_value,
            staff_entitlement=staff_value,
            requires_col_eligibility=requires_col_eligibility,
            counts_weekends=counts_weekends,
            counts_public_holidays=counts_public_holidays,
            carries_forward=carries_forward,
            enabled=enabled,
        )
    except IntegrityError as exc:
        raise ConflictError(
            "A policy already exists for this leave category."
        ) from exc


@transaction.atomic
def update_policy(
    *,
    actor,
    policy_id: int,
    faculty_entitlement,
    staff_entitlement,
    requires_col_eligibility: bool,
    counts_weekends: bool,
    counts_public_holidays: bool,
    carries_forward: bool,
    enabled: bool,
) -> LeavePolicy:
    """Update an existing current policy without creating a new version."""
    require_permission(actor, "leave.policy.manage")
    require_user_id(actor)

    policy = LeavePolicy.objects.select_for_update().filter(pk=policy_id).first()
    if policy is None:
        raise NotFoundError("Leave policy not found.")

    values = _validate_policy(
        category=policy.category,
        faculty_entitlement=faculty_entitlement,
        staff_entitlement=staff_entitlement,
        requires_col_eligibility=requires_col_eligibility,
        counts_weekends=counts_weekends,
        counts_public_holidays=counts_public_holidays,
        carries_forward=carries_forward,
        enabled=enabled,
    )

    (
        _category,
        policy.faculty_entitlement,
        policy.staff_entitlement,
        policy.requires_col_eligibility,
        policy.counts_weekends,
        policy.counts_public_holidays,
        policy.carries_forward,
        policy.enabled,
    ) = values

    try:
        policy.save()
    except IntegrityError as exc:
        raise ConflictError("The leave policy could not be updated.") from exc

    return policy


def list_policies(*, actor):
    """List current policies for an authorized administrator."""
    require_permission(actor, "leave.policy.manage")
    require_user_id(actor)
    return LeavePolicy.objects.order_by("category")

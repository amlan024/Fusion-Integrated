
"""Current leave-policy configuration for Employee Leave Management."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveTypePolicy(TimeStampedModel):
    """Current configured entitlement and validation rules for a leave type.

    Configuration is updated in place. This model deliberately has no
    draft/publish or effective-version lifecycle.
    """

    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    EMPLOYEE_KINDS = [
        ("faculty", "Faculty"),
        ("staff", "Staff"),
    ]

    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)
    employee_kind = models.CharField(
        max_length=12,
        choices=EMPLOYEE_KINDS,
    )

    annual_entitlement = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    carry_forward_allowed = models.BooleanField(default=False)
    carry_forward_limit = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    lapse_unused_balance = models.BooleanField(default=True)

    half_day_allowed = models.BooleanField(default=False)
    counts_continuous_calendar_days = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    requires_vacation_period = models.BooleanField(default=False)

    max_annual_days = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_eligible = models.BooleanField(default=True)

    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_type_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["leave_type", "employee_kind"],
                name="elm_policy_type_employee_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(annual_entitlement__isnull=True)
                    | Q(annual_entitlement__gte=0)
                ),
                name="elm_policy_entitlement_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(carry_forward_limit__isnull=True)
                    | Q(carry_forward_limit__gte=0)
                ),
                name="elm_policy_carry_limit_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(max_annual_days__isnull=True)
                    | Q(max_annual_days__gte=0)
                ),
                name="elm_policy_max_days_nonnegative",
            ),
        ]
        ordering = ["leave_type", "employee_kind"]

    def __str__(self):
        return f"{self.leave_type} policy ({self.employee_kind})"


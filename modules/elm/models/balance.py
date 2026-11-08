
"""Employee leave balances and auditable balance transactions."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Current balance for one employee, leave category and leave year."""

    leave_type = models.CharField(
        max_length=3,
        choices=[
            ("CL", "Casual Leave"),
            ("RH", "Restricted Holiday"),
            ("SCL", "Special Casual Leave"),
            ("EL", "Earned Leave"),
            ("COL", "Commuted Leave"),
            ("VL", "Vacation Leave"),
        ],
    )
    leave_year = models.PositiveSmallIntegerField()

    opening_balance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )
    credited = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    debited = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    current_balance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "leave_year"],
                name="elm_balance_employee_type_year_unique",
            ),
            models.CheckConstraint(
                condition=Q(opening_balance__gte=0),
                name="elm_balance_opening_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(credited__gte=0),
                name="elm_balance_credited_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(debited__gte=0),
                name="elm_balance_debited_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(current_balance__gte=0),
                name="elm_balance_current_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "leave_year"],
                name="elm_balance_user_year_idx",
            ),
        ]

    def __str__(self):
        return (
            f"u{self.user_id} {self.leave_type} "
            f"{self.leave_year}: {self.current_balance}"
        )


class LeaveBalanceTransaction(TimeStampedModel):
    """Immutable audit entry for a leave-account credit or debit."""

    TRANSACTION_TYPES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("lapse", "Year-end Lapse"),
        ("carry_forward", "Carry Forward"),
        ("conversion", "Leave Conversion"),
        ("reversal", "Reversal"),
        ("offline_sync", "Offline Leave Synchronization"),
        ("adjustment", "Administrative Adjustment"),
    ]

    DIRECTIONS = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )
    direction = models.CharField(max_length=6, choices=DIRECTIONS)
    units = models.DecimalField(max_digits=8, decimal_places=2)
    balance_after = models.DecimalField(max_digits=8, decimal_places=2)

    description = models.CharField(max_length=300, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    performed_by_user_id = models.IntegerField(null=True, blank=True)

    # Set by services to prevent duplicate posting when retrying an operation.
    idempotency_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "elm_leave_balance_transaction"
        constraints = [
            models.CheckConstraint(
                condition=Q(units__gt=0),
                name="elm_balance_transaction_units_positive",
            ),
            models.CheckConstraint(
                condition=Q(balance_after__gte=0),
                name="elm_balance_transaction_after_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["balance", "created_at"],
                name="elm_balance_txn_history_idx",
            ),
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return (
            f"{self.transaction_type} {self.units} "
            f"for balance {self.balance_id}"
        )


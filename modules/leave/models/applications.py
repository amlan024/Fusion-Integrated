
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]

    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=12,
        choices=[
            ("first_half", "First half"),
            ("second_half", "Second half"),
        ],
        blank=True,
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    station_leave = models.BooleanField(default=False)


    offline_recorded = models.BooleanField(default=False)
    evidence_reference = models.CharField(max_length=500, blank=True)
    offline_recorded_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="leave_user_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="leave_dates_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="leave_dates_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(half_day="")
                    | (
                        models.Q(category="CL")
                        & models.Q(start_date=models.F("end_date"))
                    )
                ),
                name="leave_half_day_cl_only",
            ),
        ]


    def __str__(self):
        return f"Leave {self.pk}: user {self.user_id} ({self.category})"


class LeaveAccount(TimeStampedModel, UserScopedModel):
    category = models.CharField(
        max_length=3,
        choices=LeaveApplication.CATEGORY_CHOICES,
    )
    year = models.PositiveSmallIntegerField()
    opening_balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    adjusted = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = "leave_account"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year"],
                name="leave_account_unique_year",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(opening_balance__gte=0)
                    & models.Q(credited__gte=0)
                    & models.Q(used__gte=0)
                    & models.Q(adjusted__gte=0)
                ),
                name="leave_account_nonnegative",
            ),
        ]

    @property
    def balance(self):
        return self.opening_balance + self.credited + self.adjusted - self.used


class LeaveDecision(TimeStampedModel):
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.PROTECT,
        related_name="decisions",
    )
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=64)
    decision = models.CharField(
        max_length=16,
        choices=[
            ("recommended", "Recommended"),
            ("not_recommended", "Not recommended"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
    )
    comments = models.TextField(blank=True)

    class Meta:
        db_table = "leave_decision"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["application", "created_at"],
                name="leave_decision_history_idx",
            ),
        ]

class LeaveCalendarEntry(TimeStampedModel):
    """A holiday, restricted holiday, or academic vacation calendar entry."""

    ENTRY_TYPES = [
        ("holiday", "Public Holiday"),
        ("rh", "Restricted Holiday"),
        ("vacation", "Academic Vacation"),
    ]

    entry_type = models.CharField(max_length=12, choices=ENTRY_TYPES)
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "leave_calendar_entry"
        constraints = [
            models.UniqueConstraint(
                fields=["entry_type", "date", "name"],
                name="leave_calendar_entry_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["entry_type", "date", "is_published"],
                name="leave_calendar_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"{self.date}: {self.name} ({self.entry_type})"



class LeavePolicy(TimeStampedModel):
    """Current configurable entitlement and counting policy per leave category."""

    category = models.CharField(
        max_length=3,
        choices=LeaveApplication.CATEGORY_CHOICES,
        unique=True,
    )
    faculty_entitlement = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )
    staff_entitlement = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )
    requires_col_eligibility = models.BooleanField(default=False)
    counts_weekends = models.BooleanField(default=False)
    counts_public_holidays = models.BooleanField(default=False)
    carries_forward = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_policy"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(faculty_entitlement__gte=0)
                    & models.Q(staff_entitlement__gte=0)
                ),
                name="leave_policy_entitlements_nonnegative",
            ),
        ]

    def __str__(self):
        return f"Leave policy: {self.category}"

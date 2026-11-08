
"""Database models for the Employee Leave Management module."""

from django.db import models
from django.db.models import Q


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE", "Pending Substitute"
    PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    CANCELLED = "CANCELLED", "Cancelled"


class LeavePolicy(models.Model):
    """Current configured leave-policy parameters."""

    category = models.CharField(
        max_length=3,
        choices=LeaveCategory.choices,
        unique=True,
    )
    annual_entitlement = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )
    maximum_accumulation = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    requires_substitute = models.BooleanField(default=False)
    requires_station_leave = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return self.get_category_display()


class LeaveBalance(models.Model):
    """Employee leave balance for a particular category and year."""

    employee_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    year = models.PositiveSmallIntegerField()
    opening_balance = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    credited = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    consumed = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    closing_balance = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee_id", "category", "year"],
                name="elm_unique_employee_leave_balance",
            ),
            models.CheckConstraint(
                condition=Q(opening_balance__gte=0)
                & Q(credited__gte=0)
                & Q(consumed__gte=0)
                & Q(closing_balance__gte=0),
                name="elm_nonnegative_leave_balances",
            ),
        ]
        indexes = [
            models.Index(fields=["employee_id", "year"]),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.category} - {self.year}"


class LeaveApplication(models.Model):
    """An employee's submitted leave application."""

    applicant_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    requested_days = models.DecimalField(max_digits=7, decimal_places=2)
    half_day = models.CharField(
        max_length=10,
        choices=[("first", "First Half"), ("second", "Second Half")],
        null=True,
        blank=True,
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
        db_index=True,
    )
    station_leave_required = models.BooleanField(default=False)
    station_address = models.TextField(blank=True)
    contact_during_leave = models.CharField(max_length=30, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_valid_application_dates",
            ),
            models.CheckConstraint(
                condition=Q(requested_days__gt=0),
                name="elm_positive_requested_days",
            ),
            models.CheckConstraint(
                condition=(
                    Q(half_day__isnull=True)
                    | Q(
                        category=LeaveCategory.CL,
                        half_day__in=["first", "second"],
                    )
                ),
                name="elm_half_day_only_for_cl",
            ),
        ]
        indexes = [
            models.Index(fields=["applicant_id", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"ELM-{self.pk}: {self.applicant_id} ({self.category})"


class SubstituteResponse(models.Model):
    """Substitute nomination and consent response."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="substitute_responses",
    )
    substitute_id = models.PositiveBigIntegerField(db_index=True)
    status = models.CharField(
        max_length=12,
        choices=[
            ("PENDING", "Pending"),
            ("ACCEPTED", "Accepted"),
            ("DECLINED", "Declined"),
        ],
        default="PENDING",
    )
    response_note = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["substitute_id", "status"]),
        ]

    def __str__(self):
        return f"Substitute {self.substitute_id} - {self.status}"


class ApprovalTask(models.Model):
    """A workflow task assigned to a reviewer or sanctioning authority."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="approval_tasks",
    )
    assigned_to_id = models.PositiveBigIntegerField(db_index=True)
    role = models.CharField(max_length=100)
    stage = models.CharField(max_length=40)
    status = models.CharField(
        max_length=12,
        choices=[
            ("PENDING", "Pending"),
            ("COMPLETED", "Completed"),
            ("CANCELLED", "Cancelled"),
        ],
        default="PENDING",
        db_index=True,
    )
    decision = models.CharField(
        max_length=20,
        choices=[
            ("RECOMMENDED", "Recommended"),
            ("NOT_RECOMMENDED", "Not Recommended"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ],
        blank=True,
    )
    comments = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["assigned_to_id", "status"]),
            models.Index(fields=["application", "stage", "status"]),
        ]

    def __str__(self):
        return f"{self.stage} - {self.application_id}"


class LeaveTransaction(models.Model):
    """Append-only record of leave balance changes."""

    employee_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="balance_transactions",
    )
    transaction_type = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    financial_year = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee_id", "category", "financial_year"]),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.transaction_type}"


class HolidayCalendar(models.Model):
    """Published holiday and restricted-holiday calendar."""

    name = models.CharField(max_length=150)
    year = models.PositiveSmallIntegerField()
    published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "year"],
                name="elm_unique_calendar_year",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.year}"


class CalendarDay(models.Model):
    """Holiday or restricted holiday in a calendar."""

    calendar = models.ForeignKey(
        HolidayCalendar,
        on_delete=models.CASCADE,
        related_name="days",
    )
    date = models.DateField()
    description = models.CharField(max_length=200)
    is_restricted_holiday = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "date"],
                name="elm_unique_calendar_day",
            ),
        ]
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} - {self.description}"


class ResumptionRecord(models.Model):
    """Employee's formal return-to-duty record."""

    application = models.OneToOneField(
        LeaveApplication,
        on_delete=models.PROTECT,
        related_name="resumption",
    )
    employee_id = models.PositiveBigIntegerField(db_index=True)
    approved_end_date = models.DateField()
    actual_resumption_date = models.DateField()
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("SUBMITTED", "Submitted"),
            ("UNDER_REVIEW", "Under Review"),
            ("VERIFIED", "Verified"),
            ("REJECTED", "Rejected"),
        ],
        default="SUBMITTED",
    )
    reviewed_by_id = models.PositiveBigIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resumption - {self.application_id}"


class OfflineLeaveRecord(models.Model):
    """Record of leave already sanctioned through an offline process."""

    employee_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    sanctioned_by_id = models.PositiveBigIntegerField()
    sanction_reference = models.CharField(max_length=150)
    evidence = models.FileField(upload_to="elm/offline_evidence/")
    synchronized = models.BooleanField(default=False)
    synchronized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_valid_offline_leave_dates",
            ),
        ]

    def __str__(self):
        return f"Offline leave - {self.employee_id}"


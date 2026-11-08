
"""Approval hierarchy, actionable workflow tasks and decision history."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.elm.models.leave_request import LeaveRequest

class ApprovalRouteStep(TimeStampedModel):
    """One step in the currently configured approval hierarchy.

    The route is resolved using the employee's organizational context,
    leave category and current configuration.
    """

    STEP_TYPES = [
        ("unit_head", "Unit Head Review"),
        ("establishment", "Establishment Verification"),
        ("sanctioning", "Final Sanctioning Authority"),
    ]

    organization_unit = models.CharField(max_length=120)
    designation = models.CharField(max_length=120, blank=True)
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
    step_order = models.PositiveSmallIntegerField()
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    approver_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)

    configured_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_approval_route_step"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization_unit",
                    "designation",
                    "leave_type",
                    "step_order",
                ],
                name="elm_route_step_unique",
            ),
            models.CheckConstraint(
                condition=Q(step_order__gt=0),
                name="elm_route_step_order_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "organization_unit",
                    "leave_type",
                    "is_active",
                ],
                name="elm_route_lookup_idx",
            ),
        ]
        ordering = ["organization_unit", "leave_type", "step_order"]

    def __str__(self):
        return (
            f"{self.organization_unit} {self.leave_type} "
            f"step {self.step_order}: {self.approver_user_id}"
        )


class WorkflowTask(TimeStampedModel):
    """An actionable task assigned to an employee or authority."""

    TASK_TYPES = [
        ("substitute", "Substitute Consent"),
        ("unit_head_review", "Unit Head Review"),
        ("establishment_review", "Establishment Review"),
        ("sanction", "Final Sanction"),
        ("cancellation", "Cancellation Review"),
        ("resumption", "Resumption Review"),
    ]

    STATUSES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("superseded", "Superseded"),
        ("cancelled", "Cancelled"),
    ]

    request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name="workflow_tasks",
    )
    task_type = models.CharField(max_length=24, choices=TASK_TYPES)
    assigned_to_user_id = models.IntegerField()
    step_order = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=12,
        choices=STATUSES,
        default="pending",
        db_index=True,
    )

    assigned_at = models.DateTimeField()
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_action = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        indexes = [
            models.Index(
                fields=["assigned_to_user_id", "status", "due_at"],
                name="elm_task_assignee_status_idx",
            ),
            models.Index(
                fields=["request", "status"],
                name="elm_task_request_status_idx",
            ),
        ]
        ordering = ["created_at", "step_order"]

    def __str__(self):
        return (
            f"{self.task_type} for request {self.request_id} "
            f"assigned to {self.assigned_to_user_id}"
        )


class WorkflowDecision(TimeStampedModel):
    """Append-only record of a workflow action and its actor."""

    ACTIONS = [
        ("substitute_accept", "Substitute Accepted"),
        ("substitute_decline", "Substitute Declined"),
        ("unit_head_approve", "Unit Head Approved"),
        ("unit_head_reject", "Unit Head Rejected"),
        ("unit_head_recommend", "Recommended"),
        ("unit_head_not_recommend", "Not Recommended"),
        ("sanction_approve", "Sanction Approved"),
        ("sanction_reject", "Sanction Rejected"),
        ("withdraw", "Withdrawn"),
        ("cancellation_approve", "Cancellation Approved"),
        ("cancellation_reject", "Cancellation Rejected"),
        ("resumption_review", "Resumption Reviewed"),
    ]

    request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name="decisions",
    )
    task = models.ForeignKey(
        WorkflowTask,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="decisions",
    )
    actor_user_id = models.IntegerField()
    action = models.CharField(max_length=30, choices=ACTIONS)
    remarks = models.TextField(blank=True)

    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)

    class Meta:
        db_table = "elm_workflow_decision"
        indexes = [
            models.Index(
                fields=["request", "created_at"],
                name="elm_decision_request_idx",
            ),
            models.Index(
                fields=["actor_user_id", "created_at"],
                name="elm_decision_actor_idx",
            ),
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.action} on request {self.request_id}"


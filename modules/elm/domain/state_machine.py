
"""State transitions for the Employee Leave Management domain."""

from modules.elm.domain.exceptions import InvalidLeaveTransitionError
from modules.elm.domain.leave_types import CL, RH

DRAFT = "draft"
PENDING_SUBSTITUTE = "pending_substitute"
PENDING_UNIT_HEAD = "pending_unit_head"
PENDING_SANCTION = "pending_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
PENDING_CANCELLATION = "pending_cancellation"
CANCELLED = "cancelled"

ACTIVE_PENDING_STATES = frozenset({
    PENDING_SUBSTITUTE,
    PENDING_UNIT_HEAD,
    PENDING_SANCTION,
})

TERMINAL_STATES = frozenset({
    REJECTED,
    WITHDRAWN,
    CANCELLED,
})

UNIT_HEAD_FINAL_TYPES = frozenset({CL, RH})

# Transitions that do not depend on the leave category.
COMMON_TRANSITIONS = {
    DRAFT: {
        "submit": PENDING_SUBSTITUTE,
        "submit_without_substitute": PENDING_UNIT_HEAD,
    },
    PENDING_SUBSTITUTE: {
        "substitute_accept": PENDING_UNIT_HEAD,
        "substitute_decline": WITHDRAWN,
        "withdraw": WITHDRAWN,
    },
    PENDING_UNIT_HEAD: {
        "withdraw": WITHDRAWN,
    },
    PENDING_SANCTION: {
        "sanction_approve": APPROVED,
        "sanction_reject": REJECTED,
        "withdraw": WITHDRAWN,
    },
    APPROVED: {
        "request_cancellation": PENDING_CANCELLATION,
    },
    PENDING_CANCELLATION: {
        "approve_cancellation": CANCELLED,
        "reject_cancellation": APPROVED,
    },
}


def allowed_actions(state: str, leave_type: str | None = None) -> tuple[str, ...]:
    """Return actions permitted from a state for the given leave category."""
    actions = dict(COMMON_TRANSITIONS.get(state, {}))

    if state == PENDING_UNIT_HEAD and leave_type is not None:
        if leave_type in UNIT_HEAD_FINAL_TYPES:
            actions["unit_head_approve"] = APPROVED
        else:
            actions["unit_head_recommend"] = PENDING_SANCTION
            actions["unit_head_not_recommend"] = PENDING_SANCTION

    return tuple(actions)


def transition(
    state: str,
    action: str,
    leave_type: str | None = None,
) -> str:
    """Return the next state after validating the requested action."""
    if state == PENDING_UNIT_HEAD:
        if leave_type is None:
            raise InvalidLeaveTransitionError(
                "Leave category is required for Unit Head decisions."
            )

        if leave_type in UNIT_HEAD_FINAL_TYPES:
            transitions = {
                "unit_head_approve": APPROVED,
                "withdraw": WITHDRAWN,
            }
        else:
            transitions = {
                "unit_head_recommend": PENDING_SANCTION,
                "unit_head_not_recommend": PENDING_SANCTION,
                "withdraw": WITHDRAWN,
            }
    else:
        transitions = COMMON_TRANSITIONS.get(state, {})

    next_state = transitions.get(action)

    if next_state is None:
        raise InvalidLeaveTransitionError(
            f"Action '{action}' is not permitted from state '{state}'."
        )

    return next_state


def is_pending(state: str) -> bool:
    """Return whether a request is awaiting an approval-stage action."""
    return state in ACTIVE_PENDING_STATES


def is_terminal(state: str) -> bool:
    """Return whether a request has reached a terminal state."""
    return state in TERMINAL_STATES

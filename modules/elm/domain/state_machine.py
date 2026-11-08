"""Pure-Python state machine for ELM leave requests."""

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
    APPROVED,
    REJECTED,
    WITHDRAWN,
    CANCELLED,
})

TRANSITIONS = {
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
        "unit_head_approve": APPROVED,
        "unit_head_recommend": PENDING_SANCTION,
        "unit_head_not_recommend": PENDING_SANCTION,
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


def allowed_actions(state: str) -> tuple[str, ...]:
    """Return all actions available from a state."""
    return tuple(TRANSITIONS.get(state, {}).keys())


def transition(state: str, action: str) -> str:
    """Return the next state or raise an error for an invalid transition."""
    from modules.elm.domain.exceptions import InvalidLeaveTransitionError

    next_state = TRANSITIONS.get(state, {}).get(action)

    if next_state is None:
        raise InvalidLeaveTransitionError(
            f"Action '{action}' is not permitted from state '{state}'."
        )

    return next_state


def is_pending(state: str) -> bool:
    """Whether a request is awaiting an action."""
    return state in ACTIVE_PENDING_STATES or state == PENDING_CANCELLATION


def is_terminal(state: str) -> bool:
    """Whether a request has reached a terminal state."""
    return state in TERMINAL_STATES

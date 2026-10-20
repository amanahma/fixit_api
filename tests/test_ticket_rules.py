from itertools import product

import pytest

from app.services.ticket_rules import (
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    TicketStatus,
    check_transition,
)

ALL_STATUSES = list(TicketStatus)


@pytest.mark.parametrize("current,target", list(product(ALL_STATUSES, ALL_STATUSES)))
def test_every_status_pair(current: TicketStatus, target: TicketStatus) -> None:
    allowed = target in ALLOWED_TRANSITIONS[current]
    if allowed:
        check_transition(current, target)
    else:
        with pytest.raises(InvalidTransition) as exc:
            check_transition(current, target)
        assert exc.value.current is current
        assert exc.value.target is target

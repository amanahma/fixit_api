from enum import StrEnum


class TicketStatus(StrEnum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_REPAIR = "IN_REPAIR"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


OPEN_STATUSES: frozenset[TicketStatus] = frozenset(
    {
        TicketStatus.NEW,
        TicketStatus.ASSIGNED,
        TicketStatus.IN_REPAIR,
        TicketStatus.READY,
    }
)

ALLOWED_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    TicketStatus.NEW: frozenset({TicketStatus.ASSIGNED, TicketStatus.CANCELLED}),
    TicketStatus.ASSIGNED: frozenset({TicketStatus.IN_REPAIR, TicketStatus.CANCELLED}),
    TicketStatus.IN_REPAIR: frozenset({TicketStatus.READY, TicketStatus.CANCELLED}),
    TicketStatus.READY: frozenset({TicketStatus.DELIVERED, TicketStatus.CANCELLED}),
    TicketStatus.DELIVERED: frozenset(),
    TicketStatus.CANCELLED: frozenset(),
}


class InvalidTransition(Exception):
    def __init__(self, current: TicketStatus, target: TicketStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot change status from {current} to {target}")


def check_transition(current: TicketStatus, target: TicketStatus) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransition(current, target)

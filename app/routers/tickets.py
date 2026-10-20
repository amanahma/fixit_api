from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import DbSession
from app.errors import ConflictError, NotFoundError
from app.models import Customer, Technician, Ticket
from app.schemas import TicketAssign, TicketCreate, TicketRead, TicketStatusChange, TicketUpdate
from app.services.ticket_rules import TicketStatus, check_transition

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=201)
async def create_ticket(body: TicketCreate, session: DbSession) -> Ticket:
    customer = await session.get(Customer, body.customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {body.customer_id} not found")
    ticket = Ticket(
        customer_id=body.customer_id,
        device=body.device,
        issue=body.issue,
        quoted_price=body.quoted_price,
        status=TicketStatus.NEW,
    )
    session.add(ticket)
    await session.flush()
    await session.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketRead])
async def list_tickets(
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: TicketStatus | None = None,
    customer_id: int | None = None,
    technician_id: int | None = None,
) -> list[Ticket]:
    stmt = (
        select(Ticket)
        .options(selectinload(Ticket.customer), selectinload(Ticket.technician))
        .order_by(Ticket.id)
    )
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if customer_id is not None:
        stmt = stmt.where(Ticket.customer_id == customer_id)
    if technician_id is not None:
        stmt = stmt.where(Ticket.technician_id == technician_id)
    result = await session.scalars(stmt.limit(limit).offset(offset))
    return list(result.all())


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: int, session: DbSession) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(ticket_id: int, body: TicketUpdate, session: DbSession) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ticket, field, value)
    await session.flush()
    await session.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/assign", response_model=TicketRead)
async def assign_ticket(ticket_id: int, body: TicketAssign, session: DbSession) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    check_transition(ticket.status, TicketStatus.ASSIGNED)

    technician = await session.get(Technician, body.technician_id)
    if technician is None:
        raise NotFoundError(f"Technician {body.technician_id} not found")
    if not technician.active:
        raise ConflictError("Cannot assign an inactive technician")

    ticket.status = TicketStatus.ASSIGNED
    ticket.technician_id = technician.id
    await session.flush()
    await session.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/status", response_model=TicketRead)
async def change_status(ticket_id: int, body: TicketStatusChange, session: DbSession) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    if body.status == TicketStatus.ASSIGNED:
        raise ConflictError("Use POST /tickets/{id}/assign to assign a technician")
    check_transition(ticket.status, body.status)
    ticket.status = body.status
    await session.flush()
    await session.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/cancel", response_model=TicketRead)
async def cancel_ticket(ticket_id: int, session: DbSession) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    check_transition(ticket.status, TicketStatus.CANCELLED)
    ticket.status = TicketStatus.CANCELLED
    await session.flush()
    await session.refresh(ticket)
    return ticket

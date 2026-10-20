from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession
from app.errors import ConflictError, NotFoundError
from app.models import Technician, Ticket
from app.schemas import TechnicianCreate, TechnicianRead, TechnicianUpdate
from app.services.ticket_rules import OPEN_STATUSES

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.post("", response_model=TechnicianRead, status_code=201)
async def create_technician(body: TechnicianCreate, session: DbSession) -> Technician:
    technician = Technician(name=body.name, phone=body.phone, active=body.active)
    session.add(technician)
    try:
        await session.flush()
        await session.refresh(technician)
    except IntegrityError as exc:
        raise ConflictError("Phone already registered") from exc
    return technician


@router.get("", response_model=list[TechnicianRead])
async def list_technicians(
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    active: bool | None = None,
) -> list[Technician]:
    stmt = select(Technician).order_by(Technician.id)
    if active is not None:
        stmt = stmt.where(Technician.active == active)
    result = await session.scalars(stmt.limit(limit).offset(offset))
    return list(result.all())


@router.get("/{technician_id}", response_model=TechnicianRead)
async def get_technician(technician_id: int, session: DbSession) -> Technician:
    technician = await session.get(Technician, technician_id)
    if technician is None:
        raise NotFoundError(f"Technician {technician_id} not found")
    return technician


@router.patch("/{technician_id}", response_model=TechnicianRead)
async def update_technician(
    technician_id: int, body: TechnicianUpdate, session: DbSession
) -> Technician:
    technician = await session.get(Technician, technician_id)
    if technician is None:
        raise NotFoundError(f"Technician {technician_id} not found")
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(technician, field, value)
    try:
        await session.flush()
        await session.refresh(technician)
    except IntegrityError as exc:
        raise ConflictError("Phone already registered") from exc
    return technician


@router.delete("/{technician_id}", status_code=204, response_class=Response)
async def delete_technician(technician_id: int, session: DbSession) -> Response:
    technician = await session.get(Technician, technician_id)
    if technician is None:
        raise NotFoundError(f"Technician {technician_id} not found")
    open_count = await session.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.technician_id == technician_id,
            Ticket.status.in_(OPEN_STATUSES),
        )
    )
    if open_count:
        raise ConflictError("Technician has open tickets")
    await session.delete(technician)
    return Response(status_code=204)

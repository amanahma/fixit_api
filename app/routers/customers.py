from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.deps import DbSession, PincodeSvc
from app.errors import ConflictError, NotFoundError
from app.models import Customer, Ticket
from app.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from app.services.ticket_rules import OPEN_STATUSES

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
async def create_customer(
    body: CustomerCreate, session: DbSession, pincodes: PincodeSvc
) -> Customer:
    district = await pincodes.require_serviceable(session, body.pincode)
    customer = Customer(
        name=body.name,
        phone=body.phone,
        pincode=body.pincode,
        district=district,
    )
    session.add(customer)
    try:
        await session.flush()
        await session.refresh(customer)
    except IntegrityError as exc:
        raise ConflictError("Phone already registered") from exc
    return customer


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Customer]:
    result = await session.scalars(
        select(Customer).order_by(Customer.id).limit(limit).offset(offset)
    )
    return list(result.all())


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: int, session: DbSession) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    session: DbSession,
    pincodes: PincodeSvc,
) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    data = body.model_dump(exclude_unset=True)
    if "pincode" in data:
        customer.district = await pincodes.require_serviceable(session, data["pincode"])
        customer.pincode = data["pincode"]
    if "name" in data:
        customer.name = data["name"]
    if "phone" in data:
        customer.phone = data["phone"]
    try:
        await session.flush()
        await session.refresh(customer)
    except IntegrityError as exc:
        raise ConflictError("Phone already registered") from exc
    return customer


@router.delete("/{customer_id}", status_code=204, response_class=Response)
async def delete_customer(customer_id: int, session: DbSession) -> Response:
    customer = await session.get(Customer, customer_id, options=[selectinload(Customer.tickets)])
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    open_count = await session.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.customer_id == customer_id,
            Ticket.status.in_(OPEN_STATUSES),
        )
    )
    if open_count:
        raise ConflictError("Customer has open tickets")
    await session.delete(customer)
    return Response(status_code=204)

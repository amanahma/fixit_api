from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.services.ticket_rules import TicketStatus


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    pincode: Mapped[str] = mapped_column(String(6), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")


class Technician(TimestampMixin, Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="technician")


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id"), nullable=True)
    device: Mapped[str] = mapped_column(String(120), nullable=False)
    issue: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(
            TicketStatus,
            name="ticket_status",
            native_enum=True,
            create_type=False,
            values_callable=lambda statuses: [item.value for item in statuses],
        ),
        nullable=False,
        default=TicketStatus.NEW,
    )
    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="tickets")
    technician: Mapped[Technician | None] = relationship(back_populates="tickets")


class PincodeCache(Base):
    __tablename__ = "pincode_cache"

    pincode: Mapped[str] = mapped_column(String(6), primary_key=True)
    districts: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

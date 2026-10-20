from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.services.ticket_rules import TicketStatus

Phone = Annotated[str, Field(pattern=r"^[6-9]\d{9}$", examples=["9876543210"])]
Pincode = Annotated[str, Field(pattern=r"^\d{6}$", examples=["110001"])]
Name = Annotated[str, Field(min_length=1, max_length=120)]


class CustomerCreate(BaseModel):
    name: Name
    phone: Phone
    pincode: Pincode


class CustomerUpdate(BaseModel):
    name: Name | None = None
    phone: Phone | None = None
    pincode: Pincode | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    pincode: str
    district: str
    created_at: datetime
    updated_at: datetime


class TechnicianCreate(BaseModel):
    name: Name
    phone: Phone
    active: bool = True


class TechnicianUpdate(BaseModel):
    name: Name | None = None
    phone: Phone | None = None
    active: bool | None = None


class TechnicianRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    active: bool
    created_at: datetime
    updated_at: datetime


class TicketCreate(BaseModel):
    customer_id: int
    device: Annotated[str, Field(min_length=1, max_length=120)]
    issue: Annotated[str, Field(min_length=1, max_length=500)]
    quoted_price: Decimal | None = Field(default=None, ge=0)


class TicketUpdate(BaseModel):
    device: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    issue: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    quoted_price: Decimal | None = Field(default=None, ge=0)


class TicketAssign(BaseModel):
    technician_id: int


class TicketStatusChange(BaseModel):
    status: TicketStatus


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    technician_id: int | None
    device: str
    issue: str
    status: TicketStatus
    quoted_price: Decimal | None
    created_at: datetime
    updated_at: datetime


class ServiceabilityRead(BaseModel):
    pincode: str
    districts: list[str]
    serviceable: bool
    matched_district: str | None


class HealthRead(BaseModel):
    status: str

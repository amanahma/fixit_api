"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ticket_status = postgresql.ENUM(
    "NEW",
    "ASSIGNED",
    "IN_REPAIR",
    "READY",
    "DELIVERED",
    "CANCELLED",
    name="ticket_status",
    create_type=False,
)


def upgrade() -> None:
    ticket_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=False),
        sa.Column("pincode", sa.String(length=6), nullable=False),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("phone", name="uq_customers_phone"),
    )
    op.create_table(
        "technicians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("phone", name="uq_technicians_phone"),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("technicians.id"), nullable=True),
        sa.Column("device", sa.String(length=120), nullable=False),
        sa.Column("issue", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            ticket_status,
            nullable=False,
            server_default="NEW",
        ),
        sa.Column("quoted_price", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"])
    op.create_index("ix_tickets_technician_id", "tickets", ["technician_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_table(
        "pincode_cache",
        sa.Column("pincode", sa.String(length=6), primary_key=True),
        sa.Column("districts", sa.JSON(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("pincode_cache")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_technician_id", table_name="tickets")
    op.drop_index("ix_tickets_customer_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("technicians")
    op.drop_table("customers")
    ticket_status.drop(op.get_bind(), checkfirst=True)

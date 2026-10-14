"""allow cancelled appointment slots to be reused

Revision ID: c42e1f7a9b30
Revises: 6da08cc305a9
Create Date: 2026-10-12
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c42e1f7a9b30"
down_revision: Union[str, None] = "6da08cc305a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_appointment_doctor_slot",
        "appointments",
        type_="unique",
    )
    op.drop_constraint(
        "uq_appointment_patient_slot",
        "appointments",
        type_="unique",
    )
    op.drop_constraint(
        "uq_appointment_patient_doctor_day",
        "appointments",
        type_="unique",
    )
    op.drop_constraint(
        "uq_appointment_doctor_daily_token",
        "appointments",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_appointment_doctor_slot",
        "appointments",
        ["doctor_id", "appointment_date", "slot_time"],
    )
    op.create_unique_constraint(
        "uq_appointment_patient_slot",
        "appointments",
        ["patient_id", "appointment_date", "slot_time"],
    )
    op.create_unique_constraint(
        "uq_appointment_patient_doctor_day",
        "appointments",
        ["patient_id", "doctor_id", "appointment_date"],
    )
    op.create_unique_constraint(
        "uq_appointment_doctor_daily_token",
        "appointments",
        ["doctor_id", "appointment_date", "token_number"],
    )

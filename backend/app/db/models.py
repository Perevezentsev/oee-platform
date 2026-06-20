"""
ORM-модели — зеркало schema.sql.
Alembic генерирует миграции из этих моделей автоматически.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Organization(Base):
    __tablename__ = "organizations"

    id:         Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]        = mapped_column(Text, nullable=False)
    slug:       Mapped[str]        = mapped_column(Text, nullable=False, unique=True)
    timezone:   Mapped[str]        = mapped_column(Text, nullable=False, default="Europe/Moscow")
    created_at: Mapped[datetime]   = mapped_column(TIMESTAMPTZ, server_default=func.now())

    users:      Mapped[list["User"]]      = relationship(back_populates="org")
    workshops:  Mapped[list["Workshop"]]  = relationship(back_populates="org")
    equipment:  Mapped[list["Equipment"]] = relationship(back_populates="org")


class User(Base):
    __tablename__ = "users"

    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:          Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    email:           Mapped[str]       = mapped_column(Text, nullable=False, unique=True)
    hashed_password: Mapped[str]       = mapped_column(Text, nullable=False)
    role:            Mapped[str]       = mapped_column(Text, nullable=False, default="operator")
    full_name:       Mapped[str | None]= mapped_column(Text)
    is_active:       Mapped[bool]      = mapped_column(Boolean, default=True)
    created_at:      Mapped[datetime]  = mapped_column(TIMESTAMPTZ, server_default=func.now())

    org: Mapped["Organization"] = relationship(back_populates="users")

    __table_args__ = (
        CheckConstraint("role IN ('operator','master','manager','admin')", name="ck_user_role"),
    )


class Workshop(Base):
    __tablename__ = "workshops"

    id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name:   Mapped[str]       = mapped_column(Text, nullable=False)

    org:       Mapped["Organization"]  = relationship(back_populates="workshops")
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="workshop")

    __table_args__ = (UniqueConstraint("org_id", "name"),)


class Equipment(Base):
    __tablename__ = "equipment"

    id:                   Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:               Mapped[uuid.UUID]  = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    workshop_id:          Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workshops.id", ondelete="SET NULL"))
    name:                 Mapped[str]        = mapped_column(Text, nullable=False)
    code:                 Mapped[str | None] = mapped_column(Text)
    ideal_cycle_time_sec: Mapped[float]      = mapped_column(Float, nullable=False)
    is_active:            Mapped[bool]       = mapped_column(Boolean, default=True)
    iot_device_id:        Mapped[str | None] = mapped_column(Text)
    data_source_type:     Mapped[str]        = mapped_column(Text, default="manual")
    created_at:           Mapped[datetime]   = mapped_column(TIMESTAMPTZ, server_default=func.now())

    org:      Mapped["Organization"] = relationship(back_populates="equipment")
    workshop: Mapped["Workshop"]     = relationship(back_populates="equipment")
    shifts:   Mapped[list["Shift"]]  = relationship(back_populates="equipment")

    __table_args__ = (
        UniqueConstraint("org_id", "code"),
        CheckConstraint("data_source_type IN ('manual','mqtt','1c','opcua')", name="ck_equipment_source"),
    )


class Shift(Base):
    __tablename__ = "shifts"

    id:                          Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_id:                Mapped[uuid.UUID]      = mapped_column(ForeignKey("equipment.id"))
    operator_id:                 Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    shift_start:                 Mapped[datetime]       = mapped_column(TIMESTAMPTZ, nullable=False)
    shift_end:                   Mapped[datetime]       = mapped_column(TIMESTAMPTZ, nullable=False)
    planned_production_time_min: Mapped[float]          = mapped_column(Float, nullable=False)
    total_parts_produced:        Mapped[int]            = mapped_column(Integer, nullable=False)
    good_parts:                  Mapped[int]            = mapped_column(Integer, nullable=False)
    availability:                Mapped[float | None]   = mapped_column(Float)
    performance:                 Mapped[float | None]   = mapped_column(Float)
    quality:                     Mapped[float | None]   = mapped_column(Float)
    oee:                         Mapped[float | None]   = mapped_column(Float)
    source:                      Mapped[str]            = mapped_column(Text, default="manual")
    notes:                       Mapped[str | None]     = mapped_column(Text)
    created_at:                  Mapped[datetime]       = mapped_column(TIMESTAMPTZ, server_default=func.now())

    equipment:       Mapped["Equipment"]          = relationship(back_populates="shifts")
    downtime_events: Mapped[list["DowntimeEvent"]] = relationship(back_populates="shift", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("shift_end > shift_start", name="ck_shift_order"),
        CheckConstraint("good_parts <= total_parts_produced", name="ck_good_lte_total"),
    )


class DowntimeEvent(Base):
    __tablename__ = "downtime_events"

    id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_id:   Mapped[uuid.UUID]      = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    reason:     Mapped[str]            = mapped_column(Text, nullable=False)
    minutes:    Mapped[float]          = mapped_column(Float, nullable=False)
    planned:    Mapped[bool]           = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None]= mapped_column(TIMESTAMPTZ)
    notes:      Mapped[str | None]     = mapped_column(Text)
    created_at: Mapped[datetime]       = mapped_column(TIMESTAMPTZ, server_default=func.now())

    shift: Mapped["Shift"] = relationship(back_populates="downtime_events")


class DowntimeReason(Base):
    __tablename__ = "downtime_reasons"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id:     Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name:       Mapped[str]       = mapped_column(Text, nullable=False)
    planned:    Mapped[bool]      = mapped_column(Boolean, default=False)
    sort_order: Mapped[int]       = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("org_id", "name"),)

"""
Pydantic-схемы для API смен.

Request  → ShiftCreate   (что присылает оператор)
Response → ShiftResponse (что возвращает API)
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Вложенные схемы
# ---------------------------------------------------------------------------

class DowntimeEventCreate(BaseModel):
    reason: str = Field(..., examples=["Переналадка"])
    minutes: float = Field(..., gt=0, examples=[87.0])
    planned: bool = False


class DowntimeEventResponse(BaseModel):
    id: UUID
    reason: str
    minutes: float
    planned: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request: оператор отправляет данные смены
# ---------------------------------------------------------------------------

class ShiftCreate(BaseModel):
    equipment_id: UUID
    shift_start: datetime
    shift_end: datetime
    planned_production_time_min: float = Field(..., gt=0, examples=[660.0])
    total_parts_produced: int = Field(..., ge=0, examples=[480])
    good_parts: int = Field(..., ge=0, examples=[461])
    notes: str | None = None
    downtime_events: list[DowntimeEventCreate] = []

    @model_validator(mode="after")
    def validate_shift(self):
        if self.shift_end <= self.shift_start:
            raise ValueError("shift_end должен быть позже shift_start")
        if self.good_parts > self.total_parts_produced:
            raise ValueError("good_parts не может быть больше total_parts_produced")
        return self


# ---------------------------------------------------------------------------
# Response: API возвращает результат с OEE
# ---------------------------------------------------------------------------

class OEESummary(BaseModel):
    oee: float
    oee_pct: float
    availability: float
    availability_pct: float
    performance: float
    performance_pct: float
    quality: float
    quality_pct: float
    actual_run_time_min: float
    total_downtime_min: float
    defect_parts: int
    downtime_pareto: list[tuple[str, float]]


class ShiftResponse(BaseModel):
    id: UUID
    equipment_id: UUID
    shift_start: datetime
    shift_end: datetime
    planned_production_time_min: float
    total_parts_produced: int
    good_parts: int
    source: str
    notes: str | None
    created_at: datetime
    oee_summary: OEESummary
    downtime_events: list[DowntimeEventResponse]

    model_config = {"from_attributes": True}


class ShiftListResponse(BaseModel):
    total: int
    items: list[ShiftResponse]
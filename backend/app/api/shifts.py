"""
Роутер смен — основной эндпоинт MVP.

POST /api/v1/shifts          — создать смену, получить OEE
GET  /api/v1/shifts          — список смен (с фильтром по equipment_id)
GET  /api/v1/shifts/{id}     — одна смена
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Shift, DowntimeEvent, Equipment
from app.oee.engine import ManualDataSource, OEECalculator
from app.api.schemas import (
    ShiftCreate, ShiftResponse, ShiftListResponse, OEESummary
)

router = APIRouter()

ds = ManualDataSource()
calc = OEECalculator()


def _build_oee_summary(result) -> OEESummary:
    return OEESummary(
        oee=result.oee,
        oee_pct=result.oee_pct,
        availability=result.availability,
        availability_pct=result.availability_pct,
        performance=result.performance,
        performance_pct=result.performance_pct,
        quality=result.quality,
        quality_pct=result.quality_pct,
        actual_run_time_min=result.actual_run_time_min,
        total_downtime_min=result.total_downtime_min,
        defect_parts=result.defect_parts,
        downtime_pareto=result.downtime_pareto,
    )


def _shift_to_response(shift: Shift, oee_summary: OEESummary) -> ShiftResponse:
    return ShiftResponse(
        id=shift.id,
        equipment_id=shift.equipment_id,
        shift_start=shift.shift_start,
        shift_end=shift.shift_end,
        planned_production_time_min=shift.planned_production_time_min,
        total_parts_produced=shift.total_parts_produced,
        good_parts=shift.good_parts,
        source=shift.source,
        notes=shift.notes,
        created_at=shift.created_at,
        oee_summary=oee_summary,
        downtime_events=shift.downtime_events,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/shifts
# ---------------------------------------------------------------------------

@router.post("/", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_shift(payload: ShiftCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем что оборудование существует
    equipment = await db.get(Equipment, payload.equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")

    # Собираем ShiftInput для OEE engine
    raw = {
        "equipment_id": str(payload.equipment_id),
        "shift_start": payload.shift_start.isoformat(),
        "shift_end": payload.shift_end.isoformat(),
        "planned_production_time_min": payload.planned_production_time_min,
        "total_parts_produced": payload.total_parts_produced,
        "good_parts": payload.good_parts,
        "ideal_cycle_time_sec": equipment.ideal_cycle_time_sec,
        "downtime_events": [
            {"reason": d.reason, "minutes": d.minutes, "planned": d.planned}
            for d in payload.downtime_events
        ],
    }

    shift_input = ds.get_shift_input(raw)
    result = calc.calculate(shift_input)

    # Сохраняем в БД
    shift = Shift(
        equipment_id=payload.equipment_id,
        shift_start=payload.shift_start,
        shift_end=payload.shift_end,
        planned_production_time_min=payload.planned_production_time_min,
        total_parts_produced=payload.total_parts_produced,
        good_parts=payload.good_parts,
        availability=result.availability,
        performance=result.performance,
        quality=result.quality,
        oee=result.oee,
        source="manual",
        notes=payload.notes,
        downtime_events=[
            DowntimeEvent(reason=d.reason, minutes=d.minutes, planned=d.planned)
            for d in payload.downtime_events
        ],
    )
    db.add(shift)
    await db.flush()  # получаем shift.id до commit

    oee_summary = _build_oee_summary(result)
    return _shift_to_response(shift, oee_summary)


# ---------------------------------------------------------------------------
# GET /api/v1/shifts
# ---------------------------------------------------------------------------

@router.get("/", response_model=ShiftListResponse)
async def list_shifts(
    equipment_id: UUID | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Shift).options(selectinload(Shift.downtime_events))

    if equipment_id:
        q = q.where(Shift.equipment_id == equipment_id)

    total_q = select(func.count()).select_from(q.subquery())
    total = await db.scalar(total_q)

    q = q.order_by(Shift.shift_start.desc()).limit(limit).offset(offset)
    shifts = (await db.execute(q)).scalars().all()

    items = []
    for shift in shifts:
        # Пересчитываем OEE из сохранённых данных для response
        equipment = await db.get(Equipment, shift.equipment_id)
        raw = {
            "equipment_id": str(shift.equipment_id),
            "shift_start": shift.shift_start.isoformat(),
            "shift_end": shift.shift_end.isoformat(),
            "planned_production_time_min": shift.planned_production_time_min,
            "total_parts_produced": shift.total_parts_produced,
            "good_parts": shift.good_parts,
            "ideal_cycle_time_sec": equipment.ideal_cycle_time_sec,
            "downtime_events": [
                {"reason": d.reason, "minutes": d.minutes, "planned": d.planned}
                for d in shift.downtime_events
            ],
        }
        result = calc.calculate(ds.get_shift_input(raw))
        items.append(_shift_to_response(shift, _build_oee_summary(result)))

    return ShiftListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# GET /api/v1/shifts/{shift_id}
# ---------------------------------------------------------------------------

@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(shift_id: UUID, db: AsyncSession = Depends(get_db)):
    q = select(Shift).where(Shift.id == shift_id).options(selectinload(Shift.downtime_events))
    shift = (await db.execute(q)).scalar_one_or_none()

    if not shift:
        raise HTTPException(status_code=404, detail="Смена не найдена")

    equipment = await db.get(Equipment, shift.equipment_id)
    raw = {
        "equipment_id": str(shift.equipment_id),
        "shift_start": shift.shift_start.isoformat(),
        "shift_end": shift.shift_end.isoformat(),
        "planned_production_time_min": shift.planned_production_time_min,
        "total_parts_produced": shift.total_parts_produced,
        "good_parts": shift.good_parts,
        "ideal_cycle_time_sec": equipment.ideal_cycle_time_sec,
        "downtime_events": [
            {"reason": d.reason, "minutes": d.minutes, "planned": d.planned}
            for d in shift.downtime_events
        ],
    }
    result = calc.calculate(ds.get_shift_input(raw))
    return _shift_to_response(shift, _build_oee_summary(result))
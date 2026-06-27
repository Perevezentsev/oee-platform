"""
Роутер дашборда.

GET /api/v1/dashboard/{equipment_id}  — все данные для дашборда одним запросом
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Shift, DowntimeEvent, Equipment

router = APIRouter()


@router.get("/{equipment_id}")
async def get_dashboard(equipment_id: UUID, db: AsyncSession = Depends(get_db)):
    equipment = await db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_ago = now - timedelta(days=30)

    # Все смены за 30 дней
    q = (
        select(Shift)
        .where(Shift.equipment_id == equipment_id)
        .where(Shift.shift_start >= month_ago)
        .where(Shift.oee.isnot(None))
        .options(selectinload(Shift.downtime_events))
        .order_by(Shift.shift_start.asc())
    )
    shifts = (await db.execute(q)).scalars().all()

    if not shifts:
        return {
            "equipment_id": str(equipment_id),
            "equipment_name": equipment.name,
            "today": None,
            "trend": [],
            "recent_shifts": [],
            "pareto": [],
        }

    # --- Сегодня: последняя смена за сегодня ---
    today_shifts = [s for s in shifts if s.shift_start >= day_start]
    today = None
    if today_shifts:
        last = today_shifts[-1]
        today = {
            "oee_pct": round(last.oee * 100, 1),
            "availability_pct": round(last.availability * 100, 1),
            "performance_pct": round(last.performance * 100, 1),
            "quality_pct": round(last.quality * 100, 1),
            "shift_start": last.shift_start.isoformat(),
            "shift_end": last.shift_end.isoformat(),
        }
    else:
        # Берём последнюю смену вообще
        last = shifts[-1]
        today = {
            "oee_pct": round(last.oee * 100, 1),
            "availability_pct": round(last.availability * 100, 1),
            "performance_pct": round(last.performance * 100, 1),
            "quality_pct": round(last.quality * 100, 1),
            "shift_start": last.shift_start.isoformat(),
            "shift_end": last.shift_end.isoformat(),
        }

    # --- Тренд: средний OEE по дням ---
    trend_map: dict[str, list[float]] = {}
    for s in shifts:
        day = s.shift_start.strftime("%Y-%m-%d")
        trend_map.setdefault(day, []).append(s.oee * 100)

    trend = [
        {"date": day, "oee_pct": round(sum(vals) / len(vals), 1)}
        for day, vals in sorted(trend_map.items())
    ]

    # --- Последние 10 смен ---
    recent = []
    for s in reversed(shifts[-10:]):
        total_dt = sum(e.minutes for e in s.downtime_events)
        recent.append({
            "id": str(s.id),
            "shift_start": s.shift_start.isoformat(),
            "oee_pct": round(s.oee * 100, 1),
            "total_parts": s.total_parts_produced,
            "good_parts": s.good_parts,
            "defect_parts": s.total_parts_produced - s.good_parts,
            "downtime_min": total_dt,
        })

    # --- Парето потерь за 30 дней ---
    pareto_map: dict[str, float] = {}
    for s in shifts:
        for e in s.downtime_events:
            pareto_map[e.reason] = pareto_map.get(e.reason, 0) + e.minutes

    pareto = [
        {"reason": reason, "minutes": round(minutes, 1)}
        for reason, minutes in sorted(pareto_map.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "equipment_id": str(equipment_id),
        "equipment_name": equipment.name,
        "today": today,
        "trend": trend,
        "recent_shifts": recent,
        "pareto": pareto,
    }
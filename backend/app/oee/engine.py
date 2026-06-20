"""
OEE Engine — ядро расчёта эффективности оборудования.

Архитектура:
  DataSource (абстракция) ← сейчас: ManualDataSource (форма оператора)
                           ← потом:  MQTTDataSource, OPCUADataSource (IoT)
  OEECalculator             — чистая математика, не зависит от источника
  OEEReport                 — итоговый отчёт по смене

Формула OEE = Availability × Performance × Quality
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import Counter


# ---------------------------------------------------------------------------
# Модели данных
# ---------------------------------------------------------------------------

@dataclass
class DowntimeEvent:
    """Один эпизод простоя."""
    reason: str          # причина: "Переналадка", "Поломка", "Ожидание материала" …
    minutes: float       # продолжительность в минутах
    planned: bool = False  # плановый (ТО, перерыв) или внеплановый


@dataclass
class ShiftInput:
    """
    Данные одной смены — то, что оператор вносит вручную (MVP).
    При подключении IoT поля заполняются автоматически из датчиков.
    """
    equipment_id: str
    shift_start: datetime
    shift_end: datetime

    planned_production_time_min: float   # плановое время работы (мин), за вычетом обедов
    total_parts_produced: int            # всего деталей выпущено
    good_parts: int                      # из них годных (без брака)
    ideal_cycle_time_sec: float          # идеальное время цикла на 1 деталь (сек)

    downtime_events: list[DowntimeEvent] = field(default_factory=list)

    def total_downtime_min(self) -> float:
        return sum(e.minutes for e in self.downtime_events)

    def unplanned_downtime_min(self) -> float:
        return sum(e.minutes for e in self.downtime_events if not e.planned)


# ---------------------------------------------------------------------------
# Абстракция источника данных (DataSource)
# ---------------------------------------------------------------------------

class DataSource(ABC):
    """
    Интерфейс источника данных.

    MVP:  ManualDataSource  — данные из REST-запроса (форма оператора).
    v2:   MQTTDataSource    — подписка на топики датчиков.
    v3:   OPCUADataSource   — промышленный протокол OPC UA.

    OEECalculator работает только с ShiftInput — не знает, откуда данные.
    """

    @abstractmethod
    def get_shift_input(self, **kwargs) -> ShiftInput:
        ...


class ManualDataSource(DataSource):
    """
    MVP: оператор заполняет форму на телефоне/браузере,
    FastAPI десериализует JSON и передаёт сюда.
    """

    def get_shift_input(self, payload: dict) -> ShiftInput:
        downtime_events = [
            DowntimeEvent(
                reason=d["reason"],
                minutes=float(d["minutes"]),
                planned=d.get("planned", False),
            )
            for d in payload.get("downtime_events", [])
        ]
        return ShiftInput(
            equipment_id=payload["equipment_id"],
            shift_start=datetime.fromisoformat(payload["shift_start"]),
            shift_end=datetime.fromisoformat(payload["shift_end"]),
            planned_production_time_min=float(payload["planned_production_time_min"]),
            total_parts_produced=int(payload["total_parts_produced"]),
            good_parts=int(payload["good_parts"]),
            ideal_cycle_time_sec=float(payload["ideal_cycle_time_sec"]),
            downtime_events=downtime_events,
        )


# ---------------------------------------------------------------------------
# Калькулятор OEE
# ---------------------------------------------------------------------------

@dataclass
class OEEResult:
    """Результат расчёта OEE для одной смены."""
    equipment_id: str
    shift_start: datetime
    shift_end: datetime

    # Три компоненты (0.0 – 1.0)
    availability: float
    performance: float
    quality: float
    oee: float

    # Абсолютные цифры для дашборда
    planned_production_time_min: float
    actual_run_time_min: float
    total_downtime_min: float
    unplanned_downtime_min: float
    total_parts: int
    good_parts: int
    defect_parts: int
    ideal_cycle_time_sec: float

    # Парето потерь (причина → минуты), отсортировано по убыванию
    downtime_pareto: list[tuple[str, float]]

    @property
    def oee_pct(self) -> float:
        return round(self.oee * 100, 1)

    @property
    def availability_pct(self) -> float:
        return round(self.availability * 100, 1)

    @property
    def performance_pct(self) -> float:
        return round(self.performance * 100, 1)

    @property
    def quality_pct(self) -> float:
        return round(self.quality * 100, 1)

    def is_world_class(self) -> bool:
        """Мировой класс: OEE ≥ 85%."""
        return self.oee >= 0.85

    def summary(self) -> str:
        lines = [
            f"=== OEE Report | {self.equipment_id} | {self.shift_start:%d.%m.%Y %H:%M} ===",
            f"  OEE          : {self.oee_pct}%"
            + (" ★ мировой класс" if self.is_world_class() else ""),
            f"  Доступность  : {self.availability_pct}%",
            f"  Производит.  : {self.performance_pct}%",
            f"  Качество     : {self.quality_pct}%",
            f"",
            f"  Плановое время  : {self.planned_production_time_min:.0f} мин",
            f"  Фактич. работа  : {self.actual_run_time_min:.0f} мин",
            f"  Простои всего   : {self.total_downtime_min:.0f} мин",
            f"    из них внепл. : {self.unplanned_downtime_min:.0f} мин",
            f"",
            f"  Всего деталей : {self.total_parts}",
            f"  Годных        : {self.good_parts}",
            f"  Брак          : {self.defect_parts}",
            f"",
            f"  Парето потерь:",
        ]
        for reason, minutes in self.downtime_pareto:
            bar = "█" * int(minutes / max(self.total_downtime_min, 1) * 20)
            lines.append(f"    {reason:<30} {minutes:>6.0f} мин  {bar}")
        return "\n".join(lines)


class OEECalculator:
    """
    Чистая математика OEE. Не знает ни про БД, ни про HTTP, ни про IoT.
    Принимает ShiftInput, возвращает OEEResult.
    """

    def calculate(self, data: ShiftInput) -> OEEResult:
        ppt = data.planned_production_time_min          # Planned Production Time
        dt  = data.total_downtime_min()                 # все простои
        udt = data.unplanned_downtime_min()             # внеплановые простои

        run_time = max(ppt - dt, 0.0)                  # фактическое время работы

        # --- Availability = Run Time / Planned Production Time ---
        availability = run_time / ppt if ppt > 0 else 0.0

        # --- Performance = (Ideal Cycle Time × Total Parts) / Run Time ---
        # Ideal cycle time переводим в минуты для единиц измерения
        ideal_ct_min = data.ideal_cycle_time_sec / 60.0
        performance = (
            (ideal_ct_min * data.total_parts_produced) / run_time
            if run_time > 0 else 0.0
        )
        performance = min(performance, 1.0)            # не может быть > 100%

        # --- Quality = Good Parts / Total Parts ---
        quality = (
            data.good_parts / data.total_parts_produced
            if data.total_parts_produced > 0 else 0.0
        )

        oee = availability * performance * quality

        # --- Парето: группируем простои по причине ---
        pareto_map: dict[str, float] = {}
        for event in data.downtime_events:
            pareto_map[event.reason] = pareto_map.get(event.reason, 0.0) + event.minutes
        pareto = sorted(pareto_map.items(), key=lambda x: x[1], reverse=True)

        return OEEResult(
            equipment_id=data.equipment_id,
            shift_start=data.shift_start,
            shift_end=data.shift_end,
            availability=availability,
            performance=performance,
            quality=quality,
            oee=oee,
            planned_production_time_min=ppt,
            actual_run_time_min=run_time,
            total_downtime_min=dt,
            unplanned_downtime_min=udt,
            total_parts=data.total_parts_produced,
            good_parts=data.good_parts,
            defect_parts=data.total_parts_produced - data.good_parts,
            ideal_cycle_time_sec=data.ideal_cycle_time_sec,
            downtime_pareto=pareto,
        )


# ---------------------------------------------------------------------------
# Агрегация по периоду (неделя / месяц для графиков тренда)
# ---------------------------------------------------------------------------

def aggregate_oee(results: list[OEEResult]) -> dict:
    """
    Считает средние компоненты OEE по списку смен.
    Используется для построения недельных/месячных трендов на дашборде.
    """
    if not results:
        return {}
    n = len(results)
    return {
        "shifts_count": n,
        "avg_oee_pct": round(sum(r.oee for r in results) / n * 100, 1),
        "avg_availability_pct": round(sum(r.availability for r in results) / n * 100, 1),
        "avg_performance_pct": round(sum(r.performance for r in results) / n * 100, 1),
        "avg_quality_pct": round(sum(r.quality for r in results) / n * 100, 1),
        "total_downtime_min": round(sum(r.total_downtime_min for r in results), 1),
        "total_good_parts": sum(r.good_parts for r in results),
        "top_loss_reason": results[0].downtime_pareto[0][0] if results[0].downtime_pareto else None,
    }


# ---------------------------------------------------------------------------
# Демо — запускается напрямую: python oee_engine.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    payload = {
        "equipment_id": "ЧПУ-1",
        "shift_start": "2025-06-20T08:00:00",
        "shift_end":   "2025-06-20T20:00:00",
        "planned_production_time_min": 660,   # 11 ч = 660 мин (без обеда)
        "total_parts_produced": 480,
        "good_parts": 461,
        "ideal_cycle_time_sec": 72,           # идеал: 1 деталь за 72 сек
        "downtime_events": [
            {"reason": "Переналадка",          "minutes": 87, "planned": False},
            {"reason": "Ожидание материала",   "minutes": 54, "planned": False},
            {"reason": "Плановое ТО",          "minutes": 30, "planned": True},
            {"reason": "Поломка",              "minutes": 22, "planned": False},
        ],
    }

    source = ManualDataSource()
    shift  = source.get_shift_input(payload)
    calc   = OEECalculator()
    result = calc.calculate(shift)

    print(result.summary())

    # Агрегация (имитируем 3 смены)
    agg = aggregate_oee([result, result, result])
    print(f"\nАгрегат по 3 сменам: OEE {agg['avg_oee_pct']}%, "
          f"главная потеря — «{agg['top_loss_reason']}»")

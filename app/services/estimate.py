"""Движок расчёта сметы.

Принимает параметры комнаты, отдаёт полную смету материалов и работ.
Содержит:
- calc_general: базовый расчёт по нормам
- calc_general_with_ml: расчёт + ML-поправка на отходы
"""
from dataclasses import dataclass, field

from app.domain.norms import (
    NORMS, REPAIR_DEPTH, LABOR_RATES,
    RepairType, ObjectType,
)


# ================= Входные и выходные структуры =================

@dataclass
class RoomInput:
    area: float
    height: float = 2.7
    object_type: ObjectType = ObjectType.FLAT
    repair_type: RepairType = RepairType.COSMETIC


@dataclass
class EstimateLine:
    category: str
    item: str
    qty: float
    unit: str
    unit_price: float = 0.0
    total: float = 0.0


@dataclass
class Estimate:
    lines: list = field(default_factory=list)
    labor_total: float = 0.0
    materials_total: float = 0.0
    grand_total: float = 0.0


# ================= Вспомогательные функции =================

def _wall_area(area: float, height: float) -> float:
    """Площадь стен, приближая комнату квадратом.

    perimeter ≈ 4 * sqrt(area), минус 15% на окна и двери.
    """
    perimeter = 4 * (area ** 0.5)
    return perimeter * height * 0.85


# ================= Базовый расчёт сметы =================

def calc_general(room: RoomInput, prices: dict) -> Estimate:
    """Считает смету по нормам.

    Args:
        room: параметры комнаты (площадь, высота, тип объекта, тип ремонта)
        prices: словарь {item: цена_за_единицу}

    Returns:
        Estimate со строками, материалами, работами и итогом.
    """
    depth = REPAIR_DEPTH[room.repair_type]
    area = room.area
    walls = _wall_area(area, room.height)
    ceiling = area

    surface_map = {
        "пол": area,
        "стены": walls,
        "потолок": ceiling,
        "электрика": area,
    }

    est = Estimate()
    for key, norm in NORMS.items():
        surface = surface_map[norm.category]
        qty = norm.per_m2 * surface * depth
        price = prices.get(key, 0.0)
        line = EstimateLine(
            category=norm.category,
            item=key,
            qty=round(qty, 2),
            unit=norm.unit,
            unit_price=price,
            total=round(qty * price, 2),
        )
        est.lines.append(line)
        est.materials_total += line.total

    est.labor_total = LABOR_RATES[room.repair_type] * area
    est.grand_total = est.materials_total + est.labor_total
    return est


# ================= Расчёт с ML-поправкой на отходы =================

def calc_general_with_ml(room: RoomInput, prices: dict,
                         catalog=None, waste_model=None) -> Estimate:
    """Расчёт сметы + обучаемая поправка на отходы.

    Если waste_model не обучена — возвращает базовую смету.
    Если catalog передан — цены берутся из result_price SKU
    (пока не реализовано, точки подключения оставлены).
    """
    est = calc_general(room, prices)

    if waste_model is None or not getattr(waste_model, "_fitted", False):
        return est

    # Поправка по каждой строке сметы
    for line in est.lines:
        factor = waste_model.predict(
            room.area, room.repair_type.value, line.category,
        )
        # Ограничиваем разумными рамками, чтобы ML не «сходила с ума»
        factor = max(0.95, min(1.30, factor))
        line.qty = round(line.qty * factor, 2)
        line.total = round(line.qty * line.unit_price, 2)

    est.materials_total = round(sum(l.total for l in est.lines), 2)
    est.grand_total = est.materials_total + est.labor_total
    return est
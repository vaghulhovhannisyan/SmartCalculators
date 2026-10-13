from dataclasses import dataclass
from enum import Enum


class ObjectType(str, Enum):
    HOUSE = "house"
    FLAT = "flat"
    STUDIO = "studio"


class RepairType(str, Enum):
    COSMETIC = "cosmetic"
    CAPITAL = "capital"
    DESIGNER = "designer"


REPAIR_DEPTH = {
    RepairType.COSMETIC: 1.0,
    RepairType.CAPITAL: 1.6,
    RepairType.DESIGNER: 2.2,
}


@dataclass(frozen=True)
class Norm:
    per_m2: float
    unit: str
    category: str


NORMS = {
    "floor_screed":   Norm(0.02, "м3", "пол"),
    "floor_tile":     Norm(1.10, "м2", "пол"),
    "floor_laminate": Norm(1.08, "м2", "пол"),
    "underlay":       Norm(1.05, "м2", "пол"),
    "wall_putty":     Norm(1.20, "кг", "стены"),
    "wall_primer":    Norm(0.15, "л",  "стены"),
    "wallpaper":      Norm(1.15, "м2", "стены"),
    "wall_paint":     Norm(0.30, "л",  "стены"),
    "tile_glue":      Norm(4.00, "кг", "стены"),
    "ceiling_paint":  Norm(0.25, "л",  "потолок"),
    "cable":          Norm(1.50, "м",  "электрика"),
    "socket":         Norm(0.20, "шт", "электрика"),
    "switch":         Norm(0.05, "шт", "электрика"),
    "junction_box":   Norm(0.08, "шт", "электрика"),
}


LABOR_RATES = {
    RepairType.COSMETIC: 3500,
    RepairType.CAPITAL: 8000,
    RepairType.DESIGNER: 15000,
}
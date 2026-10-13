"""FastAPI-приложение RepairCalc — микросервис умных калькуляторов.

Эндпоинты:
    GET  /health                       — проверка живости
    POST /api/calc/general             — общий калькулятор ремонта
    POST /api/calc/room                — калькулятор специфики помещения
    POST /api/calc/product             — расчёт в карточке товара
    POST /api/match/sku                — ML-матчинг SKU к категориям
    POST /api/match/review             — SKU, требующие ручной проверки
    GET  /api/match/product/{id}       — матчинг по карточке каталога
    POST /api/explain                  — RAG-пояснение «почему эти материалы»
"""
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.estimate import (
    calc_general, calc_general_with_ml, RoomInput,
)
from app.services.product_calc import calc_product, calc_with_packages
from app.services.catalog_client import CatalogClient, build_sku_text
from app.ml.matcher import SKUMatcher
from app.ml.recommender import score_product
from app.ml.rag import RAGKnowledgeBase
from app.ml.regression import WasteFactorModel, synth_train
from app.ml.llm import explain_estimate
from app.domain.norms import ObjectType, RepairType


# ---------- Приложение ----------
app = FastAPI(
    title="RepairCalc — Максидом Smart Calculators",
    version="1.2",
    description="Микросервис умных калькуляторов ремонта с ML-подбором материалов",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- ML-компоненты (инициализация один раз при старте) ----------
matcher = SKUMatcher()
# Передаём ту же модель, что использует matcher, — экономит 800 МБ RAM
rag = RAGKnowledgeBase(model=matcher.model)
waste_model = synth_train(WasteFactorModel())


# ---------- Каталог maxidom.ru ----------
CATALOG_BASE = os.getenv("CATALOG_BASE_URL", "https://maxidom.ru")
catalog = CatalogClient(base_url=CATALOG_BASE)


# ---------- Fallback-цены (если каталог недоступен) ----------
PRICES = {
    "floor_laminate": 1200, "wallpaper": 850, "wall_paint": 600,
    "wall_putty": 45, "floor_screed": 3500, "cable": 60,
    "socket": 250, "switch": 300, "junction_box": 90,
    "floor_tile": 1400, "tile_glue": 380, "ceiling_paint": 550,
    "underlay": 200, "wall_primer": 300,
}


# ================= Модели запросов =================

class GeneralReq(BaseModel):
    area: float = Field(gt=0)
    height: float = Field(gt=0, default=2.7)
    object_type: ObjectType
    repair_type: RepairType
    use_ml: bool = False


class RoomReq(BaseModel):
    area: float = Field(gt=0)
    height: float = Field(gt=0, default=2.7)
    room_type: Literal["санузел", "кухня", "детская", "балкон",
                       "спальня", "гостиная"]
    humidity: float = Field(ge=0, le=100, default=50.0)
    load: Literal["низкая", "средняя", "высокая"] = "средняя"
    repair_type: RepairType = RepairType.COSMETIC


class ProductReq(BaseModel):
    product_type: Literal["обои", "плитка", "ламинат", "краска", "клей_плитка"]
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    product_id: Optional[int] = None


class MatchReq(BaseModel):
    skus: list


class ExplainReq(BaseModel):
    room_type: str
    humidity: float = 50.0
    load: str = "средняя"
    estimate: dict = {}


# ================= Эндпоинты =================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "matcher_model": matcher.model.__class__.__name__,
        "categories": len(matcher.cat_names),
        "rag_docs": len(rag.docs),
        "waste_model_fitted": waste_model._fitted,
        "catalog_base": CATALOG_BASE,
    }


# ---------- Общий калькулятор ----------
@app.post("/api/calc/general")
def general(req: GeneralReq):
    room = RoomInput(req.area, req.height, req.object_type, req.repair_type)
    if req.use_ml:
        est = calc_general_with_ml(room, PRICES, waste_model=waste_model)
    else:
        est = calc_general(room, PRICES)
    return {
        "lines": [l.__dict__ for l in est.lines],
        "labor_total": est.labor_total,
        "materials_total": est.materials_total,
        "grand_total": est.grand_total,
    }


# ---------- Калькулятор помещения ----------
from app.ml.recommender import score_product, label_for

@app.post("/api/calc/room")
def room(req: RoomReq):
    est = calc_general(
        RoomInput(req.area, req.height, ObjectType.FLAT, req.repair_type),
        PRICES,
    )
    scored = []
    for l in est.lines:
        label, cat = label_for(l.item)
        sc = score_product(
            {"name": label, "description": cat},
            req.room_type, req.humidity, req.load,
        )
        scored.append({**l.__dict__, "label": label, "recommend_score": sc})
    scored.sort(key=lambda x: -x["recommend_score"])
    return {
        "room": req.room_type,
        "humidity": req.humidity,
        "load": req.load,
        "lines": scored,
        "grand_total": est.grand_total,
    }


# ---------- Карточка товара ----------
@app.post("/api/calc/product")
def product(req: ProductReq):
    # Если передан product_id — тянем карточку из каталога и считаем упаковки
    if req.product_id:
        try:
            p = catalog.product(req.product_id)
            return calc_with_packages(
                req.product_type, req.width, req.height, p,
            )
        except Exception as e:
            # Каталог недоступен — возвращаем базовый расчёт
            base = calc_product(req.product_type, req.width, req.height)
            base["warning"] = f"каталог недоступен: {e}"
            return base

    return calc_product(req.product_type, req.width, req.height)


# ---------- ML-матчинг ----------
@app.post("/api/match/sku")
def match(req: MatchReq):
    return {"results": matcher.match_batch(req.skus)}


@app.post("/api/match/review")
def match_review(req: MatchReq):
    """Только SKU, требующие ручной проверки (для админки)."""
    results = matcher.match_batch(req.skus, top_k=3)
    needs = [r for r in results if r["needs_review"]]
    auto = [r for r in results if not r["needs_review"]]
    return {
        "total": len(results),
        "auto_matched": len(auto),
        "needs_review": len(needs),
        "auto_ratio": round(len(auto) / len(results), 3) if results else 0.0,
        "review_items": needs,
    }


@app.get("/api/match/product/{product_id}")
def match_product(product_id: int):
    """Матчинг по карточке каталога — для админки."""
    try:
        p = catalog.product(product_id)
    except Exception as e:
        raise HTTPException(502, f"каталог недоступен: {e}")
    result = matcher.match_product(p)
    result["suitable_rooms"] = _infer_rooms(result["top_category"])
    result["catalog_categories"] = list((p.get("categories") or {}).values())
    return result


# ---------- RAG-пояснение ----------
@app.post("/api/explain")
async def explain(req: ExplainReq):
    context = rag.context_for(req.room_type, req.humidity, req.load)
    text = await explain_estimate(req.estimate, {
        "room_type": req.room_type,
        "humidity": req.humidity,
        "load": req.load,
        "knowledge": context,
    })
    return {
        "explanation": text,
        "context": context,
    }


# ================= Вспомогательное =================

def _infer_rooms(category: str) -> list:
    """Какие помещения подходят для категории."""
    mapping = {
        "влагостойкие_материалы": ["санузел", "кухня", "балкон"],
        "моющиеся_материалы":     ["кухня", "гостиная", "коридор"],
        "экологичные_материалы":  ["детская", "спальня"],
        "напольное_покрытие":     ["гостиная", "спальня", "коридор"],
        "стеновое_покрытие":      ["гостиная", "спальня", "детская"],
        "потолочное_покрытие":    ["гостиная", "спальня", "кухня"],
        "электрика":              ["все"],
        "сантехника":             ["санузел", "кухня"],
        "клей_и_герметик":        ["все"],
        "стяжка_и_основание":     ["все"],
    }
    return mapping.get(category, ["все"])
"""Локальная LLM через Ollama для генерации пояснений.

Используется для RAG-объяснений «почему выбраны эти материалы».
Если Ollama недоступна — возвращаем шаблонный fallback, чтобы API
не падал (LLM не в критическом пути).
"""
import os
import logging
import httpx


logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))


# ---------- Системный промпт ----------
SYSTEM_PROMPT = (
    "Ты — консультант по ремонту и отделке магазина Максидом. "
    "Отвечай кратко (3–4 предложения), по-русски, без воды. "
    "Объясняй клиенту, почему для его помещения подходят именно эти материалы, "
    "опираясь на нормативы и параметры комнаты. "
    "Не выдумывай цены и артикулы, которых нет в данных."
)


def _build_prompt(estimate: dict, room: dict) -> str:
    """Собирает промпт из сметы, параметров комнаты и RAG-контекста."""
    room_type = room.get("room_type", "помещение")
    humidity = room.get("humidity", 50)
    load = room.get("load", "средняя")
    knowledge = room.get("knowledge", "")

    # Сжимаем смету до топ-5 строк, чтобы не перегружать контекст
    lines = estimate.get("lines", [])[:5]
    lines_text = "\n".join(
        f"- {l.get('item', '?')} ({l.get('category', '?')}): "
        f"{l.get('qty', 0)} {l.get('unit', '')}"
        for l in lines
    )
    total = estimate.get("grand_total", 0)

    return f"""{SYSTEM_PROMPT}

Помещение: {room_type}, влажность {humidity}%, нагрузка {load}.
Итоговая стоимость: {total:,.0f} руб.

Основные позиции сметы:
{lines_text}

Нормативы и рекомендации:
{knowledge}

Сформулируй краткое пояснение клиенту (3–4 предложения):
почему выбраны эти материалы и как они учитывают специфику помещения.
"""


async def _call_ollama(prompt: str) -> str:
    """Прямой вызов Ollama /api/generate."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 200,
            },
        })
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip()


def _fallback_explanation(estimate: dict, room: dict) -> str:
    """Шаблонное пояснение, если LLM недоступна."""
    room_type = room.get("room_type", "помещения")
    humidity = room.get("humidity", 50)
    lines = estimate.get("lines", [])[:3]
    items = ", ".join(l.get("item", "?") for l in lines)
    return (
        f"Для {room_type} (влажность {humidity}%) подобраны материалы: {items}. "
        f"Расчёт учитывает специфику помещения и нормативы расхода. "
        f"Точные объёмы и итоговая стоимость — в смете."
    )


async def explain_estimate(estimate: dict, room: dict) -> str:
    """Возвращает пояснение сметы через локальную LLM.

    Args:
        estimate: результат calc_general / calc_room (dict)
        room: {room_type, humidity, load, knowledge}

    Returns:
        Строка с пояснением. Если Ollama недоступна — шаблонный ответ.
    """
    prompt = _build_prompt(estimate, room)
    try:
        text = await _call_ollama(prompt)
        if text:
            return text
        logger.warning("Ollama вернула пустой ответ, отдаём fallback")
        return _fallback_explanation(estimate, room)
    except httpx.ConnectError:
        logger.info("Ollama недоступна (%s), отдаём fallback", OLLAMA_URL)
        return _fallback_explanation(estimate, room)
    except httpx.TimeoutException:
        logger.warning("Ollama таймаут %.1fs, отдаём fallback", TIMEOUT)
        return _fallback_explanation(estimate, room)
    except Exception as e:
        logger.exception("LLM error: %s", e)
        return _fallback_explanation(estimate, room)
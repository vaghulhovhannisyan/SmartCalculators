"""ML-матчинг SKU к категориям работ.

Русскоязычная модель эмбеддингов + zero-shot подход: без разметки,
только текстовые описания категорий.

Модель: ai-forever/ru-en-RoSBERTa — обучена на русских каталогах,
точнее MiniLM на задаче классификации товаров.
"""
import numpy as np
from sentence_transformers import SentenceTransformer


# ---------- Модель ----------
# Альтернативы:
#   "ai-forever/ru-en-RoSBERTa"          — точнее (400 МБ), рекомендуется
#   "cointegrated/rubert-tiny2"          — быстрее и легче (30 МБ)
#   "intfloat/multilingual-e5-large"     — лучшая мультиязычная (2 ГБ)
#   "paraphrase-multilingual-MiniLM-L12-v2" — дефолт HF, слабая на русском
MODEL_NAME = "ai-forever/ru-en-RoSBERTa"

# Порог уверенности: ниже — SKU уходит в «требует проверки»
CONFIDENCE_THRESHOLD = 0.45


# ---------- Категории как связные предложения ----------
# Формулировки без лишних общих слов («материал», «товар») — они
# размывают эмбеддинги. Категория должна содержать максимум
# отличительных ключевых слов.
CATEGORIES = {
    "электрика":
        "Кабель, провод, розетка, выключатель, автоматический выключатель, "
        "электрощиток, удлинитель, монтажная коробка, гофра для кабеля",

    "сантехника":
        "Унитаз, раковина, смеситель, ванна, душевая кабина, душ, "
        "труба, сифон, полотенцесушитель, инсталляция",

    "клей_и_герметик":
        "Плиточный клей, монтажная пена, санитарный герметик, "
        "силиконовый герметик, жидкие гвозди, клеевой состав",

    "напольное_покрытие":
        "Ламинат, паркет, линолеум, керамогранит для пола, наливной пол, "
        "кварцвинил, ковролин, паркетная доска, плинтус напольный",

    "стеновое_покрытие":
        "Обои, краска для стен, декоративная штукатурка, стеновые панели, "
        "флизелиновые обои, виниловые обои, бумажные обои",

    "потолочное_покрытие":
        "Натяжной потолок, потолочная краска, потолочные панели, "
        "гипсокартон для потолка, потолочный плинтус, потолочная плитка",

    "стяжка_и_основание":
        "Стяжка, наливной пол, самовыравнивающийся пол, "
        "грунтовка глубокого проникновения, бетонконтакт, штукатурка, "
        "цементная смесь, пескобетон",

    "влагостойкие_материалы":
        "Влагостойкий гипсокартон, влагостойкая краска, керамическая плитка "
        "для ванной, нескользящая плитка, влагостойкие обои, керамогранит",

    "моющиеся_материалы":
        "Моющиеся обои, моющаяся краска, легко моющееся покрытие, "
        "жироотталкивающие обои, латексная краска",

    "экологичные_материалы":
        "Бумажные обои, краска без запаха, материалы с маркировкой E0, "
        "гипоаллергенные покрытия, безопасные для детей, водоэмульсионная краска",
}


def sku_text(name: str) -> str:
    """Возвращает текст SKU для эмбеддинга.

    Префикс убран — на русских SKU он делал все тексты похожими.
    Минимум служебных символов: только смысловые токены.
    """
    return (name or "").strip()


class SKUMatcher:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.cat_names = list(CATEGORIES.keys())
        self.cat_emb = self.model.encode(
            list(CATEGORIES.values()),
            normalize_embeddings=True,
        )

    def match(self, sku_name: str, top_k: int = 3) -> list:
        """Матчинг одного SKU."""
        text = sku_text(sku_name)
        emb = self.model.encode([text], normalize_embeddings=True)[0]
        sims = self.cat_emb @ emb
        idx = np.argsort(-sims)[:top_k]
        return [
            {
                "category": self.cat_names[i],
                "score": round(float(sims[i]), 3),
                "confident": float(sims[i]) >= CONFIDENCE_THRESHOLD,
            }
            for i in idx
        ]

    def match_batch(self, skus: list, top_k: int = 3) -> list:
        """Батчевый матчинг — быстрее в 10–50 раз."""
        if not skus:
            return []
        enriched = [sku_text(s) for s in skus]
        embs = self.model.encode(
            enriched, normalize_embeddings=True,
            batch_size=64, show_progress_bar=False,
        )
        sims = embs @ self.cat_emb.T  # (N, C)

        result = []
        for i, sku in enumerate(skus):
            order = np.argsort(-sims[i])[:top_k]
            matches = [
                {
                    "category": self.cat_names[j],
                    "score": round(float(sims[i][j]), 3),
                    "confident": float(sims[i][j]) >= CONFIDENCE_THRESHOLD,
                }
                for j in order
            ]
            top_score = matches[0]["score"]
            result.append({
                "sku": sku,
                "top_category": matches[0]["category"],
                "needs_review": top_score < CONFIDENCE_THRESHOLD,
                "matches": matches,
            })
        return result

    def match_product(self, product: dict, top_k: int = 3) -> dict:
        """Матчинг по полной карточке товара из каталога."""
        from app.services.catalog_client import build_sku_text
        text = build_sku_text(product)
        matches = self.match(text, top_k=top_k)
        return {
            "product_id": product.get("id"),
            "product_name": product.get("name"),
            "top_category": matches[0]["category"],
            "needs_review": matches[0]["score"] < CONFIDENCE_THRESHOLD,
            "matches": matches,
        }
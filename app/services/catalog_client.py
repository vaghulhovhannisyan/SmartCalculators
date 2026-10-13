"""Клиент к API каталога maxidom.ru.

Покрывает эндпоинты:
    GET /api/catalog/categories/tree
    GET /api/catalog/categories
    GET /api/catalog/products
    GET /api/catalog/products/{id}
    GET /api/regions
"""
import httpx
import math
from typing import Iterator, Optional


DEFAULT_BASE_URL = "https://maxidom.ru"


class CatalogClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, locale: str = "ru",
                 timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.locale = locale
        self.client = httpx.Client(timeout=timeout)

    # ---------- Дерево категорий ----------
    def categories_tree(self, category_id: int = 1, depth: int = 20) -> list:
        r = self.client.get(
            f"{self.base_url}/api/catalog/categories/tree",
            params={
                "category_id": category_id,
                "depth_level": depth,
                "locale": self.locale,
            },
        )
        r.raise_for_status()
        return r.json().get("data", [])

    # ---------- Сведения о категориях ----------
    def categories(self, parent_id: Optional[int] = None,
                   depth: int = 2) -> list:
        params = {"depth_level": depth, "locale": self.locale}
        if parent_id is not None:
            params["parent_id"] = parent_id
        r = self.client.get(
            f"{self.base_url}/api/catalog/categories", params=params
        )
        r.raise_for_status()
        return r.json().get("data", [])

    # ---------- Список товаров с пагинацией ----------
    def iter_products(self, category_id: int,
                      per_page: int = 20,
                      include_subsections: int = 0) -> Iterator[dict]:
        """Итератор по ВСЕМ страницам категории.

        Кейс: «одна страница не представляет весь ассортимент».
        Читаем страницы до meta.last_page.
        """
        page = 1
        while True:
            r = self.client.get(
                f"{self.base_url}/api/catalog/products",
                params={
                    "category_id": category_id,
                    "include_subsections": include_subsections,
                    "include_categories_tree": 1,
                    "per_page": per_page,
                    "page": page,
                    "locale": self.locale,
                },
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            for item in items:
                yield item
            meta = data.get("meta") or {}
            current = meta.get("current_page", page)
            last = meta.get("last_page", 1)
            if current >= last or not items:
                break
            page += 1

    # ---------- Полная карточка товара ----------
    def product(self, product_id: int) -> dict:
        """Полная карточка. В списке нет description, weight,
        characteristics — их надо тянуть отдельным запросом."""
        r = self.client.get(
            f"{self.base_url}/api/catalog/products/{product_id}",
            params={"locale": self.locale},
        )
        r.raise_for_status()
        return r.json().get("data", {})

    # ---------- Регионы ----------
    def regions(self) -> list:
        r = self.client.get(f"{self.base_url}/api/regions")
        r.raise_for_status()
        return r.json().get("data", [])


# ---------- Утилиты для работы с полями товара ----------

def get_price(product: dict) -> float:
    """result_price — источник истины (с учётом акций и региона).
    Кейс: не выбирать минимальное из ценовых полей самостоятельно."""
    for key in ("result_price", "special_price", "price"):
        v = product.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def get_package_area(product: dict) -> float:
    """Площадь одной упаковки (м²). Для штучных — 1."""
    v = product.get("package_area")
    try:
        f = float(v)
        return f if f > 0 else 1.0
    except (TypeError, ValueError):
        return 1.0


def qty_in_packages(needed_m2: float, product: dict) -> int:
    """Сколько упаковок купить под needed_m2."""
    pa = get_package_area(product)
    return max(1, math.ceil(needed_m2 / pa))


def build_sku_text(product: dict) -> str:
    """Собирает длинный текст SKU для эмбеддинга.

    Использует все доступные поля: name, marketing_description,
    description, propertiesBottom, characteristics, categories,
    brand, collection.
    """
    parts = [
        product.get("name", ""),
        product.get("marketing_description", ""),
        product.get("description", ""),
    ]
    for prop in product.get("propertiesBottom", []) or []:
        parts.append(f"{prop.get('name', '')}: {prop.get('value', '')}")
    for ch in product.get("characteristics", []) or []:
        parts.append(f"{ch.get('name', '')}: {ch.get('value', '')}")
    cats = product.get("categories") or {}
    if isinstance(cats, dict):
        parts.append(" ".join(str(v) for v in cats.values()))
    if product.get("brand"):
        parts.append(product["brand"].get("name", ""))
    if product.get("collection"):
        parts.append(product["collection"].get("name", ""))
    return " ".join(p for p in parts if p).strip()
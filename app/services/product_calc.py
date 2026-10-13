import math


def _wallpaper_rolls(wall_w: float, wall_h: float,
                     roll_w: float = 1.06, roll_l: float = 10.0) -> int:
    strips_per_roll = int(roll_l // wall_h)
    if strips_per_roll < 1:
        return 1
    strips_needed = int(wall_w // roll_w) + 1
    return max(1, -(-strips_needed // strips_per_roll))


PRODUCT_RULES = {
    "обои":        lambda w, h: _wallpaper_rolls(w, h),
    "плитка":      lambda w, h: (w * h) * 1.10,
    "ламинат":     lambda w, h: (w * h) * 1.08,
    "краска":      lambda w, h: (w * h) / 10.0,
    "клей_плитка": lambda w, h: (w * h) * 4.0,
}


def calc_product(product_type: str, width: float, height: float) -> dict:
    fn = PRODUCT_RULES.get(product_type.lower())
    if not fn:
        return {"error": "unknown_product_type"}
    qty = fn(width, height)
    unit = "шт" if product_type == "обои" else "м2/л/кг"
    return {
        "product_type": product_type,
        "qty": round(qty, 2),
        "unit": unit,
    }


def calc_with_packages(product_type: str, width: float, height: float,
                       product: dict) -> dict:
    """Расчёт с учётом package_area — кейс требует считать упаковки."""
    base = calc_product(product_type, width, height)
    if "error" in base:
        return base

    from app.services.catalog_client import (
        qty_in_packages, get_package_area, get_price,
    )

    # Для обоев qty уже в рулонах — это и есть упаковка
    if product_type == "обои":
        packages = int(base["qty"])
        base["packages"] = packages
        base["package_area"] = 1.0
    else:
        package_area = get_package_area(product)
        packages = qty_in_packages(base["qty"], product)
        base["packages"] = packages
        base["package_area"] = package_area

    price = get_price(product)
    base["unit_price"] = price
    base["total"] = round(packages * price, 2)
    return base
"""Рекомендации материалов под контекст помещения."""

ITEM_LABELS = {
    "floor_screed":   ("стяжка для пола", "пол"),
    "floor_tile":     ("керамогранитная плитка для пола влагостойкая нескользящая", "пол"),
    "floor_laminate": ("ламинат для пола износостойкий", "пол"),
    "underlay":       ("подложка под ламинат", "пол"),
    "wall_putty":     ("шпаклёвка для стен", "стены"),
    "wall_primer":    ("грунтовка для стен глубокого проникновения", "стены"),
    "wallpaper":      ("обои для стен флизелиновые влагостойкие моющиеся", "стены"),
    "wall_paint":     ("краска для стен моющаяся водоэмульсионная", "стены"),
    "tile_glue":      ("плиточный клей влагостойкий", "стены"),
    "ceiling_paint":  ("краска для потолка водоэмульсионная", "потолок"),
    "cable":          ("кабель электрический", "электрика"),
    "socket":         ("розетка встраиваемая", "электрика"),
    "switch":         ("выключатель", "электрика"),
    "junction_box":   ("монтажная коробка", "электрика"),
}

ROOM_RULES = {
    "санузел":  {"require": ["влагостойк", "плитка", "керамогранит", "нескользящ"],
                 "boost":   ["антигрибок", "влагостойк"]},
    "кухня":    {"require": ["моющ", "термостойк"],
                 "boost":   ["жироотталкивающ", "влагостойк"]},
    "детская":  {"require": ["экологичн", "безопасн"],
                 "boost":   ["гипоаллергенн", "без запаха"]},
    "балкон":   {"require": ["морозостойк", "влагостойк"],
                 "boost":   ["УФ", "влагостойк"]},
    "спальня":  {"require": ["экологичн"], "boost": ["тёпл", "тих"]},
    "гостиная": {"require": [], "boost": ["моющ", "износостойк"]},
}

def score_product(product: dict, room_type: str, humidity: float, load: str) -> float:
    rules = ROOM_RULES.get(room_type, {})
    text = (product.get("name", "") + " " + product.get("description", "")).lower()
    score = 0.0
    for kw in rules.get("require", []):
        if kw.lower() in text:
            score += 1.0
    for kw in rules.get("boost", []):
        if kw.lower() in text:
            score += 0.4
    if humidity > 70 and "влагостойк" in text:
        score += 0.8
    if load == "высокая" and ("усиленн" in text or "износостойк" in text):
        score += 0.6
    return round(score, 3)

def label_for(item_key: str) -> tuple:
    return ITEM_LABELS.get(item_key, (item_key, "прочее"))
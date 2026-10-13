"""Обучаемая ML-надстройка над нормативными формулами.

Кейс: 'обучаемые поправочные коэффициенты на реальных данных заказов —
расход на подрезку, отходы'.
"""
import numpy as np
from sklearn.linear_model import Ridge


class WasteFactorModel:
    """Предсказывает фактический коэффициент отходов.

    Обучается на паре (признаки комнаты → фактический расход / норма).
    Для MVP — обучаем на синтетике с реалистичным шумом.
    """

    def __init__(self):
        self.model = Ridge(alpha=1.0)
        self._fitted = False

    def _features(self, area: float, repair_type: str, category: str) -> list:
        # one-hot по ремонту и категории + площадь
        repairs = ["cosmetic", "capital", "designer"]
        cats = ["пол", "стены", "потолок", "электрика"]
        feat = [area, np.log1p(area)]
        feat += [1.0 if repair_type == r else 0.0 for r in repairs]
        feat += [1.0 if category == c else 0.0 for c in cats]
        return feat

    def fit(self, samples: list):
        """samples = [(area, repair_type, category, factor), ...]"""
        X = np.array([self._features(a, r, c) for a, r, c, _ in samples])
        y = np.array([f for _, _, _, f in samples])
        self.model.fit(X, y)
        self._fitted = True

    def predict(self, area: float, repair_type: str, category: str) -> float:
        if not self._fitted:
            return 1.0
        x = self._features(area, repair_type, category)
        return float(self.model.predict([x])[0])


def synth_train(model: WasteFactorModel, n: int = 500, seed: int = 42):
    """Синтетика: реалистичные коэффициенты отходов.

    Косметика: 1.02–1.08; капитальный: 1.05–1.12; дизайнерский: 1.10–1.18.
    """
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n):
        area = float(rng.uniform(4, 120))
        rt = rng.choice(["cosmetic", "capital", "designer"])
        cat = rng.choice(["пол", "стены", "потолок", "электрика"])
        base = {"cosmetic": 1.05, "capital": 1.09, "designer": 1.14}[rt]
        noise = float(rng.normal(0, 0.015))
        samples.append((area, rt, cat, base + noise))
    model.fit(samples)
    return model
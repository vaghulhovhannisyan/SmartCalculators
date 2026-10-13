"""RAG: FAISS + база знаний + Ollama/Qwen."""
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "ai-forever/ru-en-RoSBERTa"   # та же модель, что в matcher

KB_DOCS = [
    "Для санузлов и ванных комнат применяются влагостойкие материалы: "
    "керамогранит, влагостойкий гипсокартон, влагостойкие краски и грунтовки. "
    "Норматив расхода плиточного клея — 4 кг/м² при слое 5 мм.",

    "Для кухни рекомендуются моющиеся покрытия: моющиеся обои, краска "
    "для кухонь, керамическая плитка. Норматив краски — 10 м²/л.",

    "Для детских комнат применяются экологичные материалы с маркировкой "
    "E0/E1, гипоаллергенные, без запаха. Обои — бумажные или флизелиновые.",

    "Обои рассчитываются в рулонах: из рулона 10 м × 1.06 м выходит "
    "3 полосы при высоте стены 2.7 м. Запас на подрезку — 15%.",

    "Ламинат укладывается с запасом 5–8% на подрезку. Одна упаковка "
    "обычно покрывает 1.5–2.5 м² в зависимости от коллекции.",

    "Керамогранит для пола укладывается с запасом 10% на подрезку и бой. "
    "Для помещений с высокой влажностью выбирают нескользящие покрытия.",

    "Для балконов и лоджий применяются морозостойкие и влагостойкие "
    "материалы, устойчивые к УФ-излучению и перепадам температур.",
]


class RAGKnowledgeBase:
    def __init__(self, docs: list = None, model=None):
        """model — опционально готовая SentenceTransformer.

        Если передана (например, из SKUMatcher), вторая копия не грузится.
        """
        self.docs = docs or KB_DOCS
        self.model = model if model is not None else SentenceTransformer(MODEL_NAME)
        self.emb = self.model.encode(
            self.docs, normalize_embeddings=True, batch_size=32,
        )

    def search(self, query: str, top_k: int = 3) -> list:
        q = self.model.encode([query], normalize_embeddings=True)[0]
        sims = self.emb @ q
        idx = np.argsort(-sims)[:top_k]
        return [self.docs[i] for i in idx]

    def context_for(self, room_type: str, humidity: float, load: str) -> str:
        q = f"помещение {room_type} влажность {humidity} нагрузка {load} материалы расход"
        return "\n".join(self.search(q, top_k=3))
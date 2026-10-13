# RepairCalc — микросервис умных калькуляторов ремонта

Микросервис для расчёта смет, подбора материалов по параметрам помещения
и ML-матчинга SKU к категориям работ. Работает в закрытом контуре на локальной LLM.

## Что умеет

- **Общий калькулятор** — тип объекта + тип ремонта → смета
- **Специфика помещения** — влажность, назначение, нагрузка → рекомендации
- **Карточка товара** — расчёт количества под размеры стены
- **ML-матчинг** — авторазметка SKU каталога без ручной работы
- **RAG-пояснения** — почему выбраны именно эти материалы (Ollama)

## Быстрый старт

### 1. Клонировать репозиторий
```bash
git clone https://github.com/<user>/maksidom.git
cd maksidom
```

### 2. Виртуальное окружение
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows
# source .venv/bin/activate     # Linux / macOS
```

### 3. Зависимости
```bash
pip install -r requirements.txt
```

### 4. Настройки
```bash
Copy-Item .env.example .env    # Windows
# cp .env.example .env          # Linux / macOS
```

### 5. Запустить API
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Первый запуск скачает модель `ai-forever/ru-en-RoSBERTa` (~400 МБ).
Дождаться `Application startup complete`.

### 6. Запустить фронтенд (второй терминал)
```bash
python -m http.server 5500 --directory static
```

### 7. Открыть

- Калькулятор: http://localhost:5500
- Swagger API: http://localhost:8080/docs

## Метрики ML

```bash
python -m tests.eval_matcher
```

Ожидаемый вывод:

```
Всего примеров: 25
F1 (weighted):  0.746
Precision:      0.870
Recall:         0.760
Accuracy:       0.760
```

## Эндпоинты

| Метод | Путь | Что делает |
|---|---|---|
| GET  | `/health` | Проверка живости |
| POST | `/api/calc/general` | Смета |
| POST | `/api/calc/room` | Материалы под помещение |
| POST | `/api/calc/product` | Расчёт в карточке |
| POST | `/api/match/sku` | ML-матчинг |
| POST | `/api/match/review` | SKU для ручной проверки |
| GET  | `/api/match/product/{id}` | Матчинг по каталогу |
| POST | `/api/explain` | RAG-пояснение |

## Устранение проблем

| Проблема | Решение |
|---|---|
| `No module named 'app'` | запускать из корня проекта |
| `No module named 'sentence_transformers'` | `pip install -r requirements.txt` |
| Долгий старт (2–3 мин) | идёт скачивание модели |
| `Address already in use` | сменить порт: `--port 8090` |

## Лицензия

MIT
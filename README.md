# Production-style ML-сервис оценки недвижимости

[![Service checks](https://github.com/matevosovp/ML-model_deployment_in_a_cloud_infrastructure/actions/workflows/service-checks.yml/badge.svg)](https://github.com/matevosovp/ML-model_deployment_in_a_cloud_infrastructure/actions/workflows/service-checks.yml)

FastAPI-сервис для online inference CatBoost-модели с проверяемым model contract, защищённым контейнером и готовым observability-контуром на Prometheus и Grafana.

## Что доказывает проект

- контракт всех 29 признаков описан типизированной Pydantic-схемой и отображается в OpenAPI;
- строки, boolean, `NaN`, пропущенные и лишние признаки отклоняются до вызова модели;
- SHA-256, версия и feature contract артефакта закреплены в model manifest;
- startup сверяет checksum и фактический порядок признаков внутри CatBoost с HTTP-контрактом;
- liveness отделён от readiness, а старый `/service-status` сохранён как deprecated alias;
- HTTP-метрики отделены от latency и outcome model inference;
- Docker-контейнер работает от UID `10001`, без Linux capabilities и с read-only root filesystem;
- CI запускает unit/integration tests с реальным 32 MB artifact, собирает контейнер и вызывает `/predict` через его HTTP-порт;
- Prometheus datasource и Grafana dashboard provision автоматически.

## Архитектура

```text
Client
  │ POST /predict
  ▼
FastAPI ──► Pydantic contract (29 finite numeric features)
  │
  ├── startup ──► manifest ──► SHA-256 + feature-order validation
  │                                │
  │                                ▼
  └──────────────────────────► CatBoostRegressor
                                   │
             prediction + model version
                                   │
        Prometheus metrics ◄───────┘ ──► Grafana
```

## Быстрый старт

Требуются Docker и Docker Compose.

```bash
git clone https://github.com/matevosovp/ML-model_deployment_in_a_cloud_infrastructure.git
cd ML-model_deployment_in_a_cloud_infrastructure/services

cp .env.example .env
# замените GRAFANA_PASS

docker compose up --build -d
docker compose ps
```

После запуска:

| Компонент | Адрес |
|---|---|
| FastAPI | `http://127.0.0.1:8002` |
| Swagger UI | `http://127.0.0.1:8002/docs` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |

Проверка:

```bash
curl --fail http://127.0.0.1:8002/health/ready
cd ..
python services/load_test.py --requests 20 --concurrency 4
```

Локальный Python-запуск и отдельный Docker-запуск описаны в [Instructions.md](Instructions.md).

## API

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/health/live` | liveness процесса |
| `GET` | `/health/ready` | readiness проверенного model artifact |
| `POST` | `/predict` | предсказание с версией модели в ответе |
| `GET` | `/metrics` | Prometheus exposition |
| `GET` | `/docs` | Swagger UI и полный feature schema |

Эталонный payload определяется один раз в `ml_service.schemas.EXAMPLE_FEATURES` и переиспользуется тестами и load-test. Успешный ответ:

```json
{
  "user_id": 123,
  "prediction": 18429776.981288545,
  "model_version": "sprint2-catboost-2025-12-27"
}
```

## Безопасность model artifact

[`model-manifest.json`](services/models/model-manifest.json) закрепляет:

- имя артефакта;
- стабильную версию модели;
- версию feature contract;
- SHA-256 checksum.

Модель хранится в нативном бинарном формате CatBoost `.cbm`, поэтому startup не выполняет Python pickle-десериализацию. До загрузки сервис проверяет checksum, делая артефакт tamper-evident, а затем сверяет его встроенный feature order с API-схемой.

Назначение, ограничения и ожидаемое использование модели описаны в [MODEL_CARD.md](MODEL_CARD.md).

## Наблюдаемость

Основные метрики:

- `http_requests_total` — HTTP traffic по handler, method и status class;
- `http_request_duration_seconds` — end-to-end HTTP latency;
- `model_prediction_duration_seconds` — чистое время model inference;
- `model_prediction_requests_total{outcome="success|error"}` — результат попыток inference;
- `model_ready` — готовность проверенного артефакта;
- `model_info` — версия, feature contract и SHA-256 загруженной модели.

Dashboard показывает RPS, error ratio, HTTP/inference p95, readiness, CPU и счётчики inference. PromQL и базовые alert rules приведены в [Monitoring.md](Monitoring.md).

## Качество и CI

Локальные проверки:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

python -m ruff check .
python -m ruff format --check .
python -m pytest
```

GitHub Actions дополнительно:

- валидирует Docker Compose, Prometheus config, dashboard и model manifest;
- строит production image с BuildKit cache;
- запускает контейнер с read-only filesystem;
- ждёт `/health/ready` и выполняет реальный `POST /predict` через network boundary.

Dependabot еженедельно группирует обновления Python, Docker и GitHub Actions.

## Структура

```text
.
├── services/
│   ├── ml_service/
│   │   ├── main.py                 # app factory, lifecycle, endpoints, metrics
│   │   ├── schemas.py              # единственный HTTP feature contract
│   │   ├── model.py                # manifest, checksum, model adapter
│   │   ├── config.py               # environment settings
│   │   └── requirements.txt        # минимальный production runtime
│   ├── models/
│   │   ├── Sprint2_cb.cbm
│   │   └── model-manifest.json
│   ├── prometheus/                 # scrape config
│   ├── grafana/provisioning/       # datasource и dashboard provider
│   ├── Dockerfile_ml_service
│   ├── docker-compose.yaml
│   └── load_test.py                # конкурентный HTTP smoke/load test
├── tests/                          # API, failure-path и real-artifact tests
├── dashboard.json
├── MODEL_CARD.md
└── pyproject.toml
```

## Осознанные ограничения

- bundled model ожидает уже рассчитанные engineered features; следующий model version должен переносить preprocessing внутрь pipeline и принимать raw domain fields;
- сервис не имеет бизнес-аутентификации и rate limiting — Compose предназначен для локальной демонстрации за localhost;
- technical monitoring не заменяет online quality, drift и бизнес-метрики;
- для публичного deployment нужны TLS termination, secret manager и network policy.

Эксперименты и Model Registry для следующей версии модели находятся в связанном [MLflow-проекте](https://github.com/matevosovp/Mlflow-project).

# Production-style ML-сервис оценки недвижимости

[![Service checks](https://github.com/matevosovp/ML-model_deployment_in_a_cloud_infrastructure/actions/workflows/service-checks.yml/badge.svg)](https://github.com/matevosovp/ML-model_deployment_in_a_cloud_infrastructure/actions/workflows/service-checks.yml)

FastAPI-сервис для online-предсказания стоимости недвижимости с контейнеризацией и готовым observability-контуром: Prometheus собирает метрики, а Grafana автоматически подключает datasource и dashboard.

## Коротко о проекте

- строгий HTTP-контракт входных признаков через Pydantic;
- загрузка `.pkl`, `.joblib` и нативных CatBoost `.cbm` моделей;
- readiness endpoint и явная проверка загрузки модели;
- отдельные метрики HTTP latency и времени `model.predict`;
- непривилегированный пользователь внутри Docker-контейнера;
- Docker Compose с закреплёнными версиями Prometheus и Grafana;
- автоматический provisioning Grafana datasource и dashboard;
- валидный конфигурируемый load-test с mean, p50 и p95;
- секреты вынесены из Git в локальный `.env`.

## Архитектура

```text
Client
  │ POST /predict
  ▼
FastAPI + Pydantic validation
  │
  ▼
Serialized regression model
  │
  ├── prediction response
  └── Prometheus metrics ──► Prometheus ──► Grafana dashboard
```

## API

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/` | навигационный ответ |
| `GET` | `/service-status` | readiness и информация о model artifact |
| `POST` | `/predict` | предсказание стоимости объекта |
| `GET` | `/metrics` | Prometheus-compatible метрики |
| `GET` | `/docs` | Swagger UI |

`POST /predict` принимает `user_id` и словарь признаков. Сервис отклоняет отсутствующие и лишние признаки до обращения к модели, поэтому нарушение feature contract возвращается как понятная ошибка 422.

Эталонный payload находится в [`services/load_test.py`](services/load_test.py).

## Быстрый старт

Требуются Docker и Docker Compose.

```bash
git clone https://github.com/matevosovp/ML-model_deployment_in_a_cloud_infrastructure.git
cd ML-model_deployment_in_a_cloud_infrastructure/services

cp .env.example .env
# обязательно замените GRAFANA_PASS

docker compose up --build -d
docker compose ps
```

После запуска:

- API: `http://127.0.0.1:8002`
- Swagger: `http://127.0.0.1:8002/docs`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

Проверка:

```bash
curl --fail http://127.0.0.1:8002/service-status
python load_test.py --requests 10 --delay 0.25
```

Подробные варианты локального, Docker- и Compose-запуска описаны в [Instructions.md](Instructions.md).

## Наблюдаемость

Сервис разделяет метрики по слоям:

- `http_requests_total` и `http_request_duration_seconds` — HTTP-контур;
- `predict_latency_seconds` — чистое время model inference;
- `model_predictions_total` — успешные предсказания;
- `process_cpu_seconds_total` и `process_resident_memory_bytes` — runtime process.

Dashboard показывает CPU rate, p95 latency, error rate, RPS и суммарное число запросов. PromQL-запросы, интерпретация и рекомендуемые алерты описаны в [Monitoring.md](Monitoring.md).

![Grafana dashboard](dashboard.jpg)

## Безопасность и конфигурация

- `services/.env` больше не хранится в Git;
- безопасный шаблон находится в [`services/.env.example`](services/.env.example);
- Grafana не запускается с публичным паролем по умолчанию;
- сервис и observability ports привязаны к `127.0.0.1`;
- приложение запускается внутри контейнера от непривилегированного пользователя;
- подробности внутренних исключений пишутся в server log, но не возвращаются клиенту;
- Docker build context исключает секреты и runtime-файлы через `.dockerignore`.

Для внешнего deployment дополнительно необходимы reverse proxy, TLS, аутентификация, secret manager и сетевые политики.

## Структура репозитория

```text
.
├── services/
│   ├── ml_service/
│   │   ├── main.py                 # FastAPI и inference
│   │   ├── config.py               # feature contract и environment config
│   │   └── requirements.txt        # минимальные pinned runtime dependencies
│   ├── models/                     # сериализованная модель
│   ├── prometheus/prometheus.yml
│   ├── grafana/provisioning/       # datasource и dashboard provider
│   ├── Dockerfile_ml_service
│   ├── docker-compose.yaml
│   ├── load_test.py
│   └── .env.example
├── dashboard.json
├── dashboard.jpg
├── Instructions.md
└── Monitoring.md
```

## Автоматические проверки

GitHub Actions выполняет:

- установку и проверку совместимости runtime dependencies;
- компиляцию Python-кода и smoke-import FastAPI application;
- синтаксическую проверку shell scripts;
- проверку `dashboard.json`;
- валидацию итогового Docker Compose config.

## Ограничения

- model artifact поставляется вместе с учебным проектом; отдельный model registry не подключён;
- feature contract зафиксирован в коде и должен обновляться синхронно с новой моделью;
- нет аутентификации и rate limiting;
- online drift и бизнес-качество пока не измеряются;
- Compose-конфигурация предназначена для локальной демонстрации, а не публичного production.

Эксперименты и Model Registry для этой модели показаны в связанном [MLflow-проекте](https://github.com/matevosovp/Mlflow-project).

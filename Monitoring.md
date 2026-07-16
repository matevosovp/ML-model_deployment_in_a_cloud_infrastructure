# Мониторинг ML-сервиса

FastAPI экспортирует метрики на `GET /metrics`, Prometheus опрашивает сервис каждые пять секунд, а Grafana provision-ит dashboard автоматически.

## Метрики по слоям

HTTP-слой от `prometheus-fastapi-instrumentator`:

- `http_requests_total{handler,method,status}`;
- `http_request_duration_seconds_bucket{handler,method}`;
- request/response size summaries.

Model-слой:

- `model_prediction_duration_seconds` — время только внутри `LoadedModel.predict`;
- `model_prediction_requests_total{outcome="success|error"}` — bounded outcome label;
- `model_ready` — `1`, когда checksum и feature contract прошли startup validation;
- `model_info{version,feature_contract,sha256}` — идентификация artifact.

Process-слой предоставляет CPU, resident memory и Python runtime metrics.

## Основные PromQL-запросы

RPS только prediction endpoint:

```promql
sum(rate(http_requests_total{job="ml_service",handler="/predict"}[1m]))
```

Доля HTTP 4xx/5xx:

```promql
sum(rate(http_requests_total{job="ml_service",handler="/predict",status=~"4xx|5xx"}[5m]))
/
clamp_min(sum(rate(http_requests_total{job="ml_service",handler="/predict"}[5m])), 0.001)
```

P95 end-to-end HTTP latency:

```promql
histogram_quantile(
  0.95,
  sum(rate(http_request_duration_seconds_bucket{job="ml_service",handler="/predict"}[5m])) by (le)
)
```

P95 чистого inference:

```promql
histogram_quantile(
  0.95,
  sum(rate(model_prediction_duration_seconds_bucket{job="ml_service"}[5m])) by (le)
)
```

Success ratio модели:

```promql
sum(rate(model_prediction_requests_total{job="ml_service",outcome="success"}[5m]))
/
clamp_min(sum(rate(model_prediction_requests_total{job="ml_service"}[5m])), 0.001)
```

## Dashboard

`dashboard.json` содержит:

1. model readiness;
2. prediction request count за пять минут;
3. inference success ratio;
4. HTTP error ratio;
5. CPU и resident memory;
6. HTTP p95 и model inference p95;
7. prediction RPS;
8. model outcomes по bounded label.

Запросы фильтруются по `job="ml_service"` и, где необходимо, по `handler="/predict"`, поэтому scrapes `/metrics`, health probes и Swagger не искажают inference SLI.

## Базовые alert rules

Пороговые значения следует калибровать на реальной нагрузке:

- `up{job="ml_service"} == 0` или `model_ready == 0` дольше минуты;
- HTTP 5xx ratio выше 2% пять минут;
- p95 HTTP latency выше 500 ms десять минут;
- p95 inference latency выше 300 ms десять минут;
- outcome `error` растёт при стабильном трафике;
- resident memory приближается к container limit;
- CPU устойчиво выше выделенного capacity.

## Интерпретация

- одновременно растут HTTP и inference latency — проверять модель/CPU;
- растёт только HTTP latency — middleware, сеть или saturation worker;
- растёт 4xx ratio — нарушен client contract;
- растёт model outcome `error` — runtime/artifact проблема после успешной HTTP validation;
- HTTP traffic есть, а success counter не растёт — запросы не доходят до успешного inference.

Technical monitoring не измеряет ML-качество. Для production нужны feature drift, prediction distribution, delayed labels, business metric и reference-data comparison.

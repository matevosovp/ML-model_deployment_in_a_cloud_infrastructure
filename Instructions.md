# Инструкция по запуску

Все команды выполняются из корня репозитория, если не указано иное.

## Требования

- Python 3.11;
- Docker с плагином Docker Compose;
- модель `services/models/Sprint2_cb.pkl` либо собственный совместимый `.pkl`, `.joblib` или `.cbm`.

## Подготовка окружения

```bash
cd services
cp .env.example .env
```

Перед запуском:

- проверьте `MODEL_PATH` и `MODEL_FILENAME`;
- обязательно замените `GRAFANA_PASS`;
- не добавляйте `.env` в Git.

## 1. Локальный FastAPI

```bash
python3.11 -m venv ../.venv
source ../.venv/bin/activate
pip install -r ml_service/requirements.txt

bash run_stage1.sh
```

Адреса:

- Swagger UI: `http://127.0.0.1:8000/docs`
- readiness: `http://127.0.0.1:8000/service-status`
- метрики: `http://127.0.0.1:8000/metrics`

Проверка валидным запросом:

```bash
python load_test.py --url http://127.0.0.1:8000/predict --requests 1
```

## 2. Отдельный Docker-контейнер

```bash
cd services
bash run_stage2_docker.sh
```

Сервис будет доступен на `http://127.0.0.1:8001`. Скрипт самостоятельно проверит наличие `.env`, соберёт образ и запустит контейнер с непривилегированной привязкой к localhost.

Остановка выполняется через `Ctrl+C`, поскольку контейнер запускается с `--rm`.

## 3. Полный observability-контур

```bash
cd services
docker compose up --build -d
docker compose ps
```

Компоненты:

| Компонент | Адрес |
|---|---|
| FastAPI | `http://127.0.0.1:8002` |
| Swagger | `http://127.0.0.1:8002/docs` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |

Prometheus datasource и dashboard загружаются в Grafana автоматически из `services/grafana/provisioning` и корневого `dashboard.json`.

Проверки:

```bash
curl --fail http://127.0.0.1:8002/service-status
curl --fail http://127.0.0.1:8002/metrics
curl --fail "http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22ml_service%22%7D"
```

## Нагрузочная проверка

```bash
cd services
python load_test.py --requests 40 --delay 0.25
```

Скрипт отправляет корректные POST-запросы к `/predict`, выводит status и latency каждого запроса, а в конце считает mean, p50 и p95. Наличие неуспешных ответов приводит к ненулевому exit code.

Параметры:

```text
--url       endpoint предсказания
--requests  число запросов
--delay     пауза между запросами в секундах
--timeout   timeout одного запроса
```

## Остановка

```bash
cd services
docker compose down
```

Для удаления сохранённого состояния контейнеров используйте `docker compose down --volumes` только осознанно.

## Типовые проблемы

### Модель не загружается

Проверьте:

- существует ли файл по `MODEL_PATH`;
- совпадают ли версии scikit-learn, CatBoost и category-encoders с [requirements](services/ml_service/requirements.txt);
- доступен ли файл пользователю `app` внутри контейнера.

### API отвечает 422

Сервис строго проверяет список признаков. Используйте payload из `services/load_test.py` как эталон контракта.

### Prometheus не видит сервис

```bash
cd services
docker compose ps
docker compose logs ml_service prometheus
```

В Prometheus запрос `up{job="ml_service"}` должен вернуть `1`.

### Grafana не показывает dashboard

Проверьте логи и provisioning volumes:

```bash
cd services
docker compose logs grafana
docker compose config
```

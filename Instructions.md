# Инструкция по запуску

## Требования

- Python 3.12 для локальной разработки;
- Docker с Docker Compose для воспроизводимого запуска;
- доверенный model artifact и соответствующий ему manifest.

## 1. Локальная разработка

Из корня репозитория:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

cd services
bash run_stage1.sh
```

На Windows активация выполняется командой `.venv\Scripts\Activate.ps1`, а сервис можно запустить напрямую:

```powershell
$env:PYTHONPATH = "services"
.venv\Scripts\python -m uvicorn ml_service.main:app --app-dir services --host 127.0.0.1 --port 8000
```

Проверки:

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
python load_test.py --url http://127.0.0.1:8000/predict --requests 8 --concurrency 2
```

## 2. Отдельный Docker-контейнер

```bash
cd services
cp .env.example .env
bash run_stage2_docker.sh
```

Скрипт собирает image и запускает сервис на `http://127.0.0.1:8001` с non-root user, read-only root filesystem, dropped capabilities и resource limits. Остановка — `Ctrl+C`.

## 3. Полный observability-контур

```bash
cd services
cp .env.example .env
# установите собственный GRAFANA_PASS
docker compose up --build -d
docker compose ps
```

| Компонент | Адрес |
|---|---|
| FastAPI | `http://127.0.0.1:8002` |
| Swagger | `http://127.0.0.1:8002/docs` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |

```bash
curl --fail http://127.0.0.1:8002/health/ready
python load_test.py --requests 40 --concurrency 4
curl --fail "http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22ml_service%22%7D"
```

Prometheus хранит семь дней метрик в named volume. Grafana сохраняет локальное состояние, а datasource и dashboard provision автоматически.

## Конфигурация модели

По умолчанию локальный сервис использует:

- `services/models/Sprint2_cb.cbm`;
- `services/models/model-manifest.json`.

В контейнере пути задаются через `MODEL_PATH` и `MODEL_MANIFEST_PATH` в `.env`. Для нового артефакта создайте новый manifest с тем же schema version, актуальным SHA-256 и поддерживаемым feature contract. Startup завершится ошибкой, если имя, checksum или feature order не совпадают.

## Остановка и диагностика

```bash
cd services
docker compose logs ml_service prometheus grafana
docker compose down
```

Удаление volumes (`docker compose down --volumes`) стирает историю Prometheus и локальное состояние Grafana.

Типовые причины неготовности:

- model или manifest отсутствует по настроенному пути;
- SHA-256 не совпадает;
- порядок признаков артефакта отличается от `PropertyFeatures`;
- версия CatBoost не может прочитать native artifact;
- контейнеру не хватает памяти.

Точная причина пишется в startup log; наружу внутренние исключения prediction endpoint не возвращает.

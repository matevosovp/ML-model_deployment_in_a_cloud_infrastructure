# Инструкции по запуску микросервиса

Каждая инструкция выполняется из директории репозитория mle-sprint3-completed
Если необходимо перейти в поддиректорию, напишите соотвесвтующую команду

bucket = s3-student-mle-20251010-5a382f9c3d
## 1. FastAPI микросервис в виртуальном окружение
```bash
# команды создания виртуального окружения
sudo apt-get update
sudo apt-get install python3.10-venv
python3 -m venv .venv
source .venv/bin/activate
# Перейти в папку
cd services
# и установки необходимых библиотек в него

python3 -m pip install -r ml_service/requirements.txt
# команда запуска сервиса с помощью uvicorn
bash run_stage1.sh
```
После запуска:
- Swagger UI: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/service-status


### Пример curl-запроса к микросервису

```bash

curl -s -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  --data-binary @- <<'JSON'
{
  "user_id": 1,
  "features": {
    "floor": 5,
    "kitchen_area": 10.0,
    "living_area": 30.0,
    "total_area": 45.0,
    "build_year": 2008,
    "latitude": 55.75,
    "longitude": 37.62,
    "ceiling_height": 2.7,
    "floors_total": 17,
    "area_per_room": 22.5,
    "is_first_floor": 0,
    "building_age": 16,
    "is_apartment": 1,
    "ce__building_type_int": 2,
    "building_age*latitude": 892.0,
    "build_year*building_age": 32128,
    "ce__building_type_int*has_elevator": 2,
    "latitude*longitude": 2096.565,
    "building_age*longitude": 601.92,
    "floors_total*longitude": 639.54,
    "build_year*floors_total": 34136,
    "ceiling_height*latitude": 150.525,
    "build_year*rooms": 4016,
    "is_first_floor*total_area": 0.0,
    "rooms*total_area": 90.0,
    "build_year*living_area": 60240.0,
    "ceiling_height*longitude": 101.574,
    "ceiling_height*floors_total": 45.9,
    "has_elevator*is_first_floor": 0
  }
}
JSON
```


## 2. FastAPI микросервис в Docker-контейнере

```bash
# Перейти в папку
cd services
# команда для поднятия микросервиса в режиме docker 
docker build -t real-estate-ml-service -f Dockerfile_ml_service .

# Запуск
bash run_stage2_docker.sh
# команда для остановки микросервиса в режиме docker 
docker stop real-estate-ml-service
```
После запуска:
- Swagger UI: http://localhost:8001/docs
- Healthcheck: http://localhost:8001/service-status

### Пример curl-запроса к микросервису

```bash
curl -s -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "features": {
      "floor": 12,
      "kitchen_area": 13.8,
      "living_area": 41.2,
      "total_area": 62.0,
      "build_year": 2015,
      "latitude": 59.9343,
      "longitude": 30.3351,
      "ceiling_height": 2.85,
      "floors_total": 25,
      "area_per_room": 20.67,
      "is_first_floor": 0,
      "building_age": 10,
      "is_apartment": 1,
      "ce__building_type_int": 3,
      "building_age*latitude": 599.343,
      "build_year*building_age": 20150,
      "ce__building_type_int*has_elevator": 3,
      "latitude*longitude": 1817.031,
      "building_age*longitude": 303.351,
      "floors_total*longitude": 758.3775,
      "build_year*floors_total": 50375,
      "ceiling_height*latitude": 170.812,
      "build_year*rooms": 6045,
      "is_first_floor*total_area": 0.0,
      "rooms*total_area": 186.0,
      "build_year*living_area": 83018.0,
      "ceiling_height*longitude": 86.455,
      "ceiling_height*floors_total": 71.25,
      "has_elevator*is_first_floor": 0
    }
  }'
```

## 3. Docker compose для микросервиса и системы моониторинга

```bash
# команда перехода в нужную директорию
cd services
# команда для запуска микросервиса в режиме docker compose
docker compose down
docker compose up --build


```

Адреса:

Микросервис: http://localhost:8002

Swagger: http://localhost:8002/docs

Метрики: http://localhost:8002/metrics

Prometheus: http://localhost:9090

Grafana: http://localhost:3000

### Пример curl-запроса к микросервису


#### Проверка, что Prometheus видит сервис:
```bash
curl -s "http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22ml_service%22%7D"

```
#### Проверка, что метрики доступны:
```bash
curl -s http://127.0.0.1:8002/metrics | head -n 20
```
## 4. Скрипт симуляции нагрузки
Скрипт 40 раз с паузой 2 секунды отправляет GET-запросы на /predict с параметрами x=0..39 и y=-16, делая дополнительную паузу 30 секунд на 30-й итерации.

### команды необходимые для запуска скрипта

```bash
cd services
python3 test_requests_2.py
python3 test_requests_1.py

```
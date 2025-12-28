import os
import logging
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BASE_DIR / "models"

# Имя файла модели. По умолчанию Sprint2_cb.pkl, переопределяется через env при необходимости
MODEL_FILENAME = os.getenv("MODEL_FILENAME", "Sprint2_cb.pkl")

# Полный путь к модели. Можно полностью переопределить через env MODEL_PATH
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(MODELS_DIR / MODEL_FILENAME)))

LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

# Список фичей, которые ожидает модель
REQUIRED_FEATURES = [
    "floor",
    "kitchen_area",
    "living_area",
    "total_area",
    "build_year",
    "latitude",
    "longitude",
    "ceiling_height",
    "floors_total",
    "area_per_room",
    "is_first_floor",
    "building_age",
    "is_apartment",
    "ce__building_type_int",
    "building_age*latitude",
    "build_year*building_age",
    "ce__building_type_int*has_elevator",
    "latitude*longitude",
    "building_age*longitude",
    "floors_total*longitude",
    "build_year*floors_total",
    "ceiling_height*latitude",
    "build_year*rooms",
    "is_first_floor*total_area",
    "rooms*total_area",
    "build_year*living_area",
    "ceiling_height*longitude",
    "ceiling_height*floors_total",
    "has_elevator*is_first_floor",
]

from __future__ import annotations
import os
import time
import logging
from typing import Any, Dict, Union
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import joblib
from catboost import CatBoostRegressor
from fastapi import Body
from prometheus_fastapi_instrumentator import Instrumentator
import time
from prometheus_client import Counter, Histogram


PREDICT_LATENCY_SECONDS = Histogram(
    "predict_latency_seconds",
    "Latency of /predict endpoint in seconds"
)

POSITIVE_PREDICTIONS_TOTAL = Counter(
    "positive_predictions_total",
    "Number of positive predictions (prediction > 0)"
)




MODEL_FILENAME = "Sprint2_cb.pkl"

logger = logging.getLogger("ml_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

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

def load_model(model_path: str) -> Any:
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    ext = os.path.splitext(model_path)[1].lower()

    if ext in [".pkl", ".joblib"]:
        if joblib is None:
            raise RuntimeError("joblib is not installed but model file is .pkl or .joblib")
        return joblib.load(model_path)

    if ext == ".cbm":
        if CatBoostRegressor is None:
            raise RuntimeError("catboost is not installed but model file is .cbm")
        model = CatBoostRegressor()
        model.load_model(model_path)
        return model

    raise RuntimeError(f"Unsupported model extension: {ext}")


class PredictRequest(BaseModel):
    user_id: int = Field(..., examples=[123])
    features: Dict[str, Union[float, int, str, bool]] = Field(
        ...,
        examples=[
            {
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
        ],
        description="Признаки одного объекта. Ключи должны совпадать с тем, что ожидает модель",
    )


class PredictResponse(BaseModel):
    user_id: int
    prediction: float


app = FastAPI(
    title="Real Estate Price ML Service",
    version="1.0.0",
    description="Онлайн сервис предсказания цены недвижимости",
)

Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
)

BASE_DIR = Path(__file__).resolve().parents[1]  # папка services/
DEFAULT_MODEL_PATH = BASE_DIR / "models" / MODEL_FILENAME
MODEL_PATH = os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH))


@app.on_event("startup")
def startup_event() -> None:
    try:
        model = load_model(MODEL_PATH)

        try:
            if model.__class__.__name__ == "PyFuncModel" and model.__class__.__module__.startswith("mlflow"):
                if not hasattr(model, "_model_id"):
                    model._model_id = "local_pyfunc_model"
        except Exception:
            pass

        app.state.model = model
        logger.info("Model loaded from %s", MODEL_PATH)
    except Exception:
        logger.exception("Failed to load model")
        raise


@app.get("/")
def root():
    return {"message": "Service is up. Open /docs or /service-status."}

@app.get("/service-status")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(
    req: PredictRequest = Body(
        ...,
        examples={
            "valid_request": {
                "summary": "Пример корректного запроса",
                "value": {
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
                },
            }
        },
    )
):
    model = getattr(app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=500, detail="Model is not loaded")

    if not req.features:
        raise HTTPException(status_code=400, detail="features must be non-empty")

    # Проверяем, что набор фичей ровно такой, как ожидает модель
    missing = [c for c in REQUIRED_FEATURES if c not in req.features]
    extra = [c for c in req.features.keys() if c not in REQUIRED_FEATURES]

    if missing or extra:
        raise HTTPException(
            status_code=422,
            detail={
                "missing_features": missing,
                "extra_features": extra,
                "required_features_count": len(REQUIRED_FEATURES),
            },
        )

    try:
        # Собираем DataFrame строго в нужном порядке колонок
        x = pd.DataFrame([req.features], columns=REQUIRED_FEATURES)

        t0 = time.perf_counter()
        y_pred = model.predict(x)
        latency = time.perf_counter() - t0

        if hasattr(y_pred, "__len__"):
            pred_value = float(y_pred[0])
        else:
            pred_value = float(y_pred)

        # Этап 4: обновляем метрики Prometheus
        PREDICT_LATENCY_SECONDS.observe(latency)
        if pred_value > 0:
            POSITIVE_PREDICTIONS_TOTAL.inc()


        logger.info(
            "Predicted user_id=%s prediction=%.6f latency=%.6fs",
            req.user_id,
            pred_value,
            latency,
        )


        return PredictResponse(user_id=req.user_id, prediction=pred_value)

    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=400,
            detail=(
                "Prediction failed. Check feature names and types. "
                f"Error: {type(e).__name__}: {e}"
            ),
        )


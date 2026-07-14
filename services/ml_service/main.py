from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import joblib
from catboost import CatBoostRegressor
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

from .config import MODEL_PATH, LOG_LEVEL, REQUIRED_FEATURES


PREDICT_LATENCY_SECONDS = Histogram(
    "predict_latency_seconds",
    "Latency of model prediction in seconds"
)

PREDICTIONS_TOTAL = Counter(
    "model_predictions_total",
    "Number of successful model predictions",
)


logger = logging.getLogger("ml_service")
logging.basicConfig(level=LOG_LEVEL)


def load_model(model_path: Path) -> Any:
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    ext = model_path.suffix.lower()

    if ext in [".pkl", ".joblib"]:
        return joblib.load(model_path)

    if ext == ".cbm":
        model = CatBoostRegressor()
        model.load_model(str(model_path))
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


@app.on_event("startup")
def startup_event() -> None:
    try:
        model = load_model(MODEL_PATH)

        # Если это MLflow PyFuncModel, добавляем служебный id (не критично, но удобно)
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
def health_check() -> Dict[str, Union[str, bool]]:
    model_loaded = getattr(app.state, "model", None) is not None
    return {
        "status": "ok" if model_loaded else "not_ready",
        "model_loaded": model_loaded,
        "model_file": MODEL_PATH.name,
    }


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
        x = pd.DataFrame([req.features], columns=REQUIRED_FEATURES)

        t0 = time.perf_counter()
        y_pred = model.predict(x)
        latency = time.perf_counter() - t0

        if hasattr(y_pred, "__len__"):
            pred_value = float(y_pred[0])
        else:
            pred_value = float(y_pred)

        PREDICT_LATENCY_SECONDS.observe(latency)
        PREDICTIONS_TOTAL.inc()

        logger.info(
            "Predicted user_id=%s prediction=%.6f latency=%.6fs",
            req.user_id,
            pred_value,
            latency,
        )

        return PredictResponse(user_id=req.user_id, prediction=pred_value)

    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed inside the model service",
        ) from exc

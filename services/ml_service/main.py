from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .model import LoadedModel, load_model
from .schemas import (
    LivenessResponse,
    PredictRequest,
    PredictResponse,
    ReadinessResponse,
)

APP_VERSION = "2.0.0"

PREDICTION_DURATION_SECONDS = Histogram(
    "model_prediction_duration_seconds",
    "Time spent inside model prediction in seconds",
)
PREDICTION_REQUESTS_TOTAL = Counter(
    "model_prediction_requests_total",
    "Model prediction attempts grouped by bounded outcome",
    labelnames=("outcome",),
)
MODEL_READY = Gauge(
    "model_ready",
    "Whether a validated model artifact is loaded",
)
MODEL_INFO = Info(
    "model",
    "Loaded model metadata",
)

ModelLoader = Callable[[Settings], LoadedModel]
logger = logging.getLogger("ml_service")


def create_app(
    settings: Settings | None = None,
    *,
    model_loader: ModelLoader = load_model,
    instrument_metrics: bool = True,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    logging.basicConfig(
        level=resolved_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        MODEL_READY.set(0)
        try:
            runtime = await run_in_threadpool(model_loader, resolved_settings)
        except Exception:
            logger.exception("Model startup validation failed")
            raise

        application.state.model = runtime
        MODEL_READY.set(1)
        MODEL_INFO.info(
            {
                "version": runtime.model_version,
                "feature_contract": runtime.feature_contract,
                "sha256": runtime.sha256,
            }
        )
        logger.info(
            "Model ready version=%s feature_contract=%s sha256=%s",
            runtime.model_version,
            runtime.feature_contract,
            runtime.sha256,
        )

        try:
            yield
        finally:
            application.state.model = None
            MODEL_READY.set(0)

    application = FastAPI(
        title="Real Estate Price ML Service",
        version=APP_VERSION,
        description=(
            "Typed online inference service with a checksum-verified CatBoost artifact, "
            "readiness probes, and Prometheus metrics."
        ),
        lifespan=lifespan,
    )

    if instrument_metrics:
        Instrumentator(
            excluded_handlers=["/metrics"],
        ).instrument(application).expose(
            application,
            endpoint="/metrics",
            include_in_schema=False,
        )

    @application.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {
            "service": application.title,
            "version": APP_VERSION,
            "docs": "/docs",
            "readiness": "/health/ready",
        }

    @application.get("/health/live", response_model=LivenessResponse, tags=["health"])
    def liveness() -> LivenessResponse:
        return LivenessResponse()

    @application.get(
        "/health/ready",
        response_model=ReadinessResponse,
        tags=["health"],
    )
    @application.get(
        "/service-status",
        response_model=ReadinessResponse,
        tags=["health"],
        deprecated=True,
        include_in_schema=False,
    )
    def readiness(response: Response) -> ReadinessResponse:
        runtime = getattr(application.state, "model", None)
        if runtime is None:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessResponse(status="not_ready", model_loaded=False)

        return ReadinessResponse(
            status="ready",
            model_loaded=True,
            model_version=runtime.model_version,
            feature_contract=runtime.feature_contract,
        )

    @application.post(
        "/predict",
        response_model=PredictResponse,
        tags=["inference"],
    )
    def predict(request: PredictRequest) -> PredictResponse:
        runtime: LoadedModel | None = getattr(application.state, "model", None)
        if runtime is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model is not ready",
            )

        started_at = time.perf_counter()
        try:
            prediction = runtime.predict(request.features.as_model_input())
        except Exception as exc:
            PREDICTION_REQUESTS_TOTAL.labels(outcome="error").inc()
            logger.exception("Prediction failed user_id=%s", request.user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Prediction failed inside the model service",
            ) from exc
        finally:
            PREDICTION_DURATION_SECONDS.observe(time.perf_counter() - started_at)

        PREDICTION_REQUESTS_TOTAL.labels(outcome="success").inc()
        logger.debug("Prediction completed user_id=%s", request.user_id)
        return PredictResponse(
            user_id=request.user_id,
            prediction=prediction,
            model_version=runtime.model_version,
        )

    return application


app = create_app()

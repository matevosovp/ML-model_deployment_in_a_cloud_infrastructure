from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ml_service.config import Settings
from ml_service.main import create_app
from ml_service.model import LoadedModel
from ml_service.schemas import EXAMPLE_FEATURES, EXPECTED_FEATURES


class FakeModel:
    def __init__(self, result: Any = 12_345_678.9) -> None:
        self.result = result
        self.columns: tuple[str, ...] | None = None

    def predict(self, frame: Any) -> Any:
        self.columns = tuple(frame.columns)
        if isinstance(self.result, Exception):
            raise self.result
        return np.asarray([self.result])


def make_runtime(model: Any | None = None) -> LoadedModel:
    return LoadedModel(
        model=model or FakeModel(),
        model_version="test-model-v1",
        feature_contract="engineered-real-estate-v1",
        sha256="0" * 64,
        feature_names=EXPECTED_FEATURES,
    )


def make_client(runtime: LoadedModel) -> TestClient:
    settings = Settings(
        model_path=Path("unused.cbm"),
        model_manifest_path=Path("unused.json"),
        log_level=20,
    )
    app = create_app(
        settings,
        model_loader=lambda _: runtime,
        instrument_metrics=False,
    )
    return TestClient(app, raise_server_exceptions=False)


def valid_payload() -> dict[str, Any]:
    return {"user_id": 123, "features": deepcopy(EXAMPLE_FEATURES)}


def test_health_and_prediction_contract() -> None:
    fake_model = FakeModel()
    with make_client(make_runtime(fake_model)) as client:
        assert client.get("/health/live").json() == {"status": "ok"}

        readiness = client.get("/health/ready")
        assert readiness.status_code == 200
        assert readiness.json() == {
            "status": "ready",
            "model_loaded": True,
            "model_version": "test-model-v1",
            "feature_contract": "engineered-real-estate-v1",
        }

        response = client.post("/predict", json=valid_payload())

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 123,
        "prediction": 12_345_678.9,
        "model_version": "test-model-v1",
    }
    assert fake_model.columns == EXPECTED_FEATURES


def test_endpoints_report_not_ready_before_lifespan() -> None:
    client = make_client(make_runtime())
    try:
        assert client.get("/").status_code == 200
        readiness = client.get("/health/ready")
        prediction = client.post("/predict", json=valid_payload())
    finally:
        client.close()

    assert readiness.status_code == 503
    assert readiness.json()["status"] == "not_ready"
    assert prediction.status_code == 503
    assert prediction.json() == {"detail": "Model is not ready"}


def test_schema_rejects_strings_booleans_missing_and_extra_features() -> None:
    invalid_values = ["12", True, None]
    with make_client(make_runtime()) as client:
        for invalid in invalid_values:
            payload = valid_payload()
            payload["features"]["floor"] = invalid
            assert client.post("/predict", json=payload).status_code == 422

        missing = valid_payload()
        del missing["features"]["floor"]
        assert client.post("/predict", json=missing).status_code == 422

        extra = valid_payload()
        extra["features"]["unexpected"] = 1
        assert client.post("/predict", json=extra).status_code == 422


def test_schema_rejects_non_positive_and_non_integer_user_ids() -> None:
    with make_client(make_runtime()) as client:
        for invalid in (0, -1, True, "123"):
            payload = valid_payload()
            payload["user_id"] = invalid
            assert client.post("/predict", json=payload).status_code == 422


def test_schema_rejects_inconsistent_engineered_features() -> None:
    payload = valid_payload()
    payload["features"]["building_age*latitude"] = 1

    with make_client(make_runtime()) as client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 422
    assert "inconsistent engineered features" in response.text


def test_prediction_errors_do_not_leak_internal_details() -> None:
    runtime = make_runtime(FakeModel(RuntimeError("secret internal detail")))
    with make_client(runtime) as client:
        response = client.post("/predict", json=valid_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Prediction failed inside the model service"}
    assert "secret" not in response.text


@pytest.mark.parametrize("result", [[1.0, 2.0], float("nan")])
def test_model_rejects_invalid_prediction_shape_or_value(result: Any) -> None:
    runtime = make_runtime(FakeModel(result))

    with pytest.raises(RuntimeError):
        runtime.predict(EXAMPLE_FEATURES)


def test_openapi_exposes_each_required_feature() -> None:
    with make_client(make_runtime()) as client:
        schema = client.get("/openapi.json").json()

    features_schema = schema["components"]["schemas"]["PropertyFeatures"]
    assert tuple(features_schema["properties"]) == EXPECTED_FEATURES
    assert set(features_schema["required"]) == set(EXPECTED_FEATURES)
    assert features_schema["additionalProperties"] is False

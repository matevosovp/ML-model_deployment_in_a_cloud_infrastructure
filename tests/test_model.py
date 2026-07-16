from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from ml_service.config import Settings
from ml_service.main import app
from ml_service.model import ModelContractError, load_model
from ml_service.schemas import EXAMPLE_FEATURES, EXPECTED_FEATURES, PropertyFeatures


def test_settings_reject_invalid_log_level_and_resolve_relative_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_PATH", "models/custom.cbm")
    monkeypatch.setenv("LOG_LEVEL", "not-a-level")

    with pytest.raises(ValueError, match="Unsupported LOG_LEVEL"):
        Settings.from_env()


@pytest.mark.integration
def test_bundled_artifact_loads_and_predicts() -> None:
    runtime = load_model(Settings.from_env())
    features = PropertyFeatures.model_validate(EXAMPLE_FEATURES).as_model_input()
    prediction = runtime.predict(features)

    assert runtime.feature_names == EXPECTED_FEATURES
    assert runtime.model_version == "sprint2-catboost-2025-12-27"
    assert math.isfinite(prediction)
    assert prediction > 0


@pytest.mark.integration
def test_full_application_lifecycle_and_metrics() -> None:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={"user_id": 1, "features": EXAMPLE_FEATURES},
        )
        metrics = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["model_version"] == "sprint2-catboost-2025-12-27"
    assert metrics.status_code == 200
    assert "model_prediction_requests_total" in metrics.text
    assert 'outcome="success"' in metrics.text
    assert "model_ready 1.0" in metrics.text


def test_checksum_mismatch_fails_before_deserialization(tmp_path: Path) -> None:
    artifact = tmp_path / "model.cbm"
    artifact.write_bytes(b"not a valid native model")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact": artifact.name,
                "model_version": "test",
                "feature_contract": "engineered-real-estate-v1",
                "sha256": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        model_path=artifact,
        model_manifest_path=manifest,
        log_level=20,
    )

    with pytest.raises(ModelContractError, match="checksum mismatch"):
        load_model(settings)

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from .config import Settings
from .schemas import EXPECTED_FEATURES, FEATURE_CONTRACT_VERSION

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ModelContractError(RuntimeError):
    """The artifact, its manifest, and the HTTP feature contract disagree."""


@dataclass(frozen=True, slots=True)
class ModelManifest:
    artifact: str
    model_version: str
    feature_contract: str
    sha256: str

    @classmethod
    def load(cls, path: Path) -> ModelManifest:
        if not path.is_file():
            raise FileNotFoundError(f"Model manifest not found: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelContractError(f"Cannot read model manifest: {path}") from exc

        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ModelContractError("Model manifest schema_version must be 1")

        expected_keys = {
            "schema_version",
            "artifact",
            "model_version",
            "feature_contract",
            "sha256",
        }
        if set(payload) != expected_keys:
            raise ModelContractError("Model manifest keys do not match the supported schema")

        values = {
            key: payload[key]
            for key in ("artifact", "model_version", "feature_contract", "sha256")
        }
        if not all(isinstance(value, str) and value for value in values.values()):
            raise ModelContractError("Model manifest values must be non-empty strings")

        artifact = values["artifact"]
        if Path(artifact).name != artifact:
            raise ModelContractError("Model manifest artifact must be a filename")

        checksum = values["sha256"].lower()
        if not SHA256_PATTERN.fullmatch(checksum):
            raise ModelContractError("Model manifest sha256 must contain 64 hex characters")

        if values["feature_contract"] != FEATURE_CONTRACT_VERSION:
            raise ModelContractError(
                "Model manifest references an unsupported feature contract: "
                f"{values['feature_contract']}"
            )

        return cls(
            artifact=artifact,
            model_version=values["model_version"],
            feature_contract=values["feature_contract"],
            sha256=checksum,
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_artifact(path: Path) -> Any:
    extension = path.suffix.lower()
    if extension != ".cbm":
        raise ModelContractError(
            f"Only native CatBoost .cbm artifacts are supported, got: {extension or '<none>'}"
        )

    model = CatBoostRegressor()
    model.load_model(str(path))
    return model


def _model_feature_names(model: Any) -> tuple[str, ...]:
    feature_names = getattr(model, "feature_names_", None)
    if not feature_names:
        feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is None:
        raise ModelContractError("Model artifact does not expose feature names")
    return tuple(str(name) for name in feature_names)


@dataclass(frozen=True, slots=True)
class LoadedModel:
    model: Any
    model_version: str
    feature_contract: str
    sha256: str
    feature_names: tuple[str, ...]

    def predict(self, features: Mapping[str, float]) -> float:
        frame = pd.DataFrame([features], columns=self.feature_names)
        raw_prediction = self.model.predict(frame)
        values = np.asarray(raw_prediction, dtype=float).reshape(-1)

        if values.size != 1:
            raise RuntimeError(f"Model returned {values.size} predictions for one input row")

        prediction = float(values[0])
        if not math.isfinite(prediction):
            raise RuntimeError("Model returned a non-finite prediction")
        return prediction


def load_model(settings: Settings) -> LoadedModel:
    manifest = ModelManifest.load(settings.model_manifest_path)
    model_path = settings.model_path

    if not model_path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")
    if model_path.name != manifest.artifact:
        raise ModelContractError(f"Manifest expects {manifest.artifact}, got {model_path.name}")

    actual_checksum = sha256_file(model_path)
    if actual_checksum != manifest.sha256:
        raise ModelContractError(
            "Model checksum mismatch: the artifact may be corrupt or unreviewed"
        )

    model = _load_artifact(model_path)
    feature_names = _model_feature_names(model)
    if feature_names != EXPECTED_FEATURES:
        raise ModelContractError("Model feature order does not match the HTTP feature contract")

    return LoadedModel(
        model=model,
        model_version=manifest.model_version,
        feature_contract=manifest.feature_contract,
        sha256=actual_checksum,
        feature_names=feature_names,
    )

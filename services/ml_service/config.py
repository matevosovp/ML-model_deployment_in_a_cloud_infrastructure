from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = SERVICES_DIR / "models"


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = SERVICES_DIR / path
    return path.resolve()


def _log_level_from_env() -> int:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported LOG_LEVEL: {level_name}")
    return level


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration resolved independently for every app instance."""

    model_path: Path
    model_manifest_path: Path
    log_level: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            model_path=_path_from_env(
                "MODEL_PATH",
                MODELS_DIR / "Sprint2_cb.cbm",
            ),
            model_manifest_path=_path_from_env(
                "MODEL_MANIFEST_PATH",
                MODELS_DIR / "model-manifest.json",
            ),
            log_level=_log_level_from_env(),
        )

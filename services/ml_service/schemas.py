from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

FEATURE_CONTRACT_VERSION = "engineered-real-estate-v1"


def _strict_finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a JSON number, not a string or boolean")

    number = float(value)
    if not math.isfinite(number):
        raise ValueError("value must be finite")
    return number


FeatureValue = Annotated[float, BeforeValidator(_strict_finite_number)]
PositiveUserId = Annotated[int, Field(strict=True, gt=0)]
AreaValue = Annotated[FeatureValue, Field(ge=0, le=10_000)]
BinaryValue = Annotated[FeatureValue, Field(ge=0, le=1)]


class PropertyFeatures(BaseModel):
    """Exact, ordered feature contract expected by the bundled CatBoost model."""

    model_config = ConfigDict(extra="forbid", populate_by_name=False)

    floor: Annotated[FeatureValue, Field(ge=-5, le=250)]
    kitchen_area: AreaValue
    living_area: AreaValue
    total_area: Annotated[FeatureValue, Field(gt=0, le=10_000)]
    build_year: Annotated[FeatureValue, Field(ge=1700, le=2100)]
    latitude: Annotated[FeatureValue, Field(ge=-90, le=90)]
    longitude: Annotated[FeatureValue, Field(ge=-180, le=180)]
    ceiling_height: Annotated[FeatureValue, Field(gt=0, le=20)]
    floors_total: Annotated[FeatureValue, Field(gt=0, le=250)]
    area_per_room: Annotated[FeatureValue, Field(gt=0, le=10_000)]
    is_first_floor: BinaryValue
    building_age: Annotated[FeatureValue, Field(ge=0, le=500)]
    is_apartment: BinaryValue
    ce_building_type_int: FeatureValue = Field(alias="ce__building_type_int")
    building_age_x_latitude: FeatureValue = Field(alias="building_age*latitude")
    build_year_x_building_age: FeatureValue = Field(alias="build_year*building_age")
    building_type_x_has_elevator: FeatureValue = Field(alias="ce__building_type_int*has_elevator")
    latitude_x_longitude: FeatureValue = Field(alias="latitude*longitude")
    building_age_x_longitude: FeatureValue = Field(alias="building_age*longitude")
    floors_total_x_longitude: FeatureValue = Field(alias="floors_total*longitude")
    build_year_x_floors_total: FeatureValue = Field(alias="build_year*floors_total")
    ceiling_height_x_latitude: FeatureValue = Field(alias="ceiling_height*latitude")
    build_year_x_rooms: FeatureValue = Field(alias="build_year*rooms")
    is_first_floor_x_total_area: FeatureValue = Field(alias="is_first_floor*total_area")
    rooms_x_total_area: FeatureValue = Field(alias="rooms*total_area")
    build_year_x_living_area: FeatureValue = Field(alias="build_year*living_area")
    ceiling_height_x_longitude: FeatureValue = Field(alias="ceiling_height*longitude")
    ceiling_height_x_floors_total: FeatureValue = Field(alias="ceiling_height*floors_total")
    has_elevator_x_is_first_floor: FeatureValue = Field(alias="has_elevator*is_first_floor")

    @model_validator(mode="after")
    def validate_feature_consistency(self) -> PropertyFeatures:
        if self.is_first_floor not in {0.0, 1.0} or self.is_apartment not in {0.0, 1.0}:
            raise ValueError("binary features must be exactly 0 or 1")
        if self.floor > self.floors_total:
            raise ValueError("floor cannot exceed floors_total")
        if self.kitchen_area + self.living_area > self.total_area * 1.01:
            raise ValueError("kitchen_area + living_area cannot exceed total_area")

        expected_interactions = {
            "building_age*latitude": (
                self.building_age_x_latitude,
                self.building_age * self.latitude,
            ),
            "build_year*building_age": (
                self.build_year_x_building_age,
                self.build_year * self.building_age,
            ),
            "latitude*longitude": (
                self.latitude_x_longitude,
                self.latitude * self.longitude,
            ),
            "building_age*longitude": (
                self.building_age_x_longitude,
                self.building_age * self.longitude,
            ),
            "floors_total*longitude": (
                self.floors_total_x_longitude,
                self.floors_total * self.longitude,
            ),
            "build_year*floors_total": (
                self.build_year_x_floors_total,
                self.build_year * self.floors_total,
            ),
            "ceiling_height*latitude": (
                self.ceiling_height_x_latitude,
                self.ceiling_height * self.latitude,
            ),
            "is_first_floor*total_area": (
                self.is_first_floor_x_total_area,
                self.is_first_floor * self.total_area,
            ),
            "build_year*living_area": (
                self.build_year_x_living_area,
                self.build_year * self.living_area,
            ),
            "ceiling_height*longitude": (
                self.ceiling_height_x_longitude,
                self.ceiling_height * self.longitude,
            ),
            "ceiling_height*floors_total": (
                self.ceiling_height_x_floors_total,
                self.ceiling_height * self.floors_total,
            ),
        }
        inconsistent = [
            name
            for name, (actual, expected) in expected_interactions.items()
            if not math.isclose(actual, expected, rel_tol=1e-3, abs_tol=1e-2)
        ]
        if inconsistent:
            raise ValueError("inconsistent engineered features: " + ", ".join(inconsistent))
        return self

    def as_model_input(self) -> dict[str, float]:
        return self.model_dump(by_alias=True)


EXPECTED_FEATURES = tuple(
    field.alias or name for name, field in PropertyFeatures.model_fields.items()
)

EXAMPLE_FEATURES: dict[str, int | float] = {
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
    "has_elevator*is_first_floor": 0,
}


class PredictRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"user_id": 123, "features": EXAMPLE_FEATURES}]},
    )

    user_id: PositiveUserId
    features: PropertyFeatures


class PredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    user_id: int
    prediction: float
    model_version: str


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ready", "not_ready"]
    model_loaded: bool
    model_version: str | None = None
    feature_contract: str = FEATURE_CONTRACT_VERSION

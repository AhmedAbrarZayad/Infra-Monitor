import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

FEATURE_NAMES = ("cpu_r", "mem_u", "disk_r", "disk_w", "eth1_fi", "eth1_fo")


class FeatureRow(BaseModel):
    timestamp: datetime
    values: dict[str, float]

    @field_validator("values")
    @classmethod
    def validate_values(cls, values):
        if tuple(values) != FEATURE_NAMES:
            raise ValueError("values must use the ordered container_iforest_v1 schema")
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("feature values must be finite")
        return values


class TrainRequest(BaseModel):
    service_id: UUID
    feature_names: list[str]
    rows: list[FeatureRow] = Field(min_length=2)
    contamination: float = Field(default=0.05, gt=0, le=0.5)

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, names):
        if tuple(names) != FEATURE_NAMES:
            raise ValueError("feature_names must match container_iforest_v1")
        return names


class InferRequest(BaseModel):
    organization_id: UUID
    server_id: UUID
    service_id: UUID
    window_started_at: datetime
    window_ended_at: datetime
    rows: list[FeatureRow] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_window(self):
        if self.window_started_at >= self.window_ended_at:
            raise ValueError("window_started_at must be earlier than window_ended_at")
        return self

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from shared.contracts import JobStatusType

Point = tuple[Annotated[StrictInt, Field(ge=0)], Annotated[StrictInt, Field(ge=0)]]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    status: Literal["uploaded"] = "uploaded"


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line: tuple[Point, Point] | None = None

    @model_validator(mode="after")
    def distinct_points(self):
        if self.line is not None and self.line[0] == self.line[1]:
            raise ValueError("Точки линии должны различаться")
        return self


class JobActionResponse(BaseModel):
    job_id: str
    status: JobStatusType


class StatsResponse(BaseModel):
    job_id: str
    entered: int = 0
    exited: int = 0
    current: int = 0
    fps: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    progress: float | None = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    status: JobStatusType = "uploaded"
    error: str | None = None

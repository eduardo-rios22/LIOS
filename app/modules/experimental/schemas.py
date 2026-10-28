from typing import Literal

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    age: int = Field(ge=18, le=110)
    country: str = Field(min_length=1, max_length=120)
    experience: str = Field(min_length=1, max_length=8)
    consent: bool


class StartResponse(BaseModel):
    session_id: str
    condition: str


class RoundRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=36)
    round: int = Field(ge=1, le=10)
    chosen: Literal["A", "B"]
    duration_seconds: int = Field(ge=0)


class RoundResponse(BaseModel):
    session_id: str
    round: int
    chosen: str
    recommended: str
    consistent: str
    error: bool
    accepted: bool


class FinishRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=36)
    iu1: int = Field(ge=1, le=7)
    iu2: int = Field(ge=1, le=7)
    iu3: int = Field(ge=1, le=7)
    check_error: int = Field(ge=1, le=7)
    check_explanation: int = Field(ge=1, le=7)


class FinishResponse(BaseModel):
    ok: bool

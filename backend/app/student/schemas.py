from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferred_difficulty: Literal["easy", "medium", "hard"]


class Counts(BaseModel):
    courses: int
    materials: int
    submitted_attempts: int
    feedback: int


class EnrolledCourse(BaseModel):
    id: UUID
    title: str
    joined_at: datetime


class Dashboard(BaseModel):
    preferences: Preferences
    counts: Counts
    courses: list[EnrolledCourse]


class Attempt(BaseModel):
    id: UUID
    title: str
    kind: Literal["classroom", "practice"]
    state: Literal["in_progress", "submitted", "expired"]
    attempt_number: int
    started_at: datetime
    submitted_at: datetime | None


class AttemptPage(BaseModel):
    items: list[Attempt]
    total: int
    offset: int
    limit: int

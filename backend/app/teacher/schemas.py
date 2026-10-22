from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Enter a nonblank title without control characters")
        return value


class TopicInput(CourseInput):
    """The same short-title rules apply to a topic name."""


class Topic(BaseModel):
    id: UUID
    name: str


class Course(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    topic_count: int


class CoursePage(BaseModel):
    items: list[Course]
    total: int
    offset: int
    limit: int


class CourseDetail(Course):
    topics: list[Topic]


class Counts(BaseModel):
    courses: int
    materials: int
    questions: int
    assessments: int


class AssessmentSummary(BaseModel):
    id: UUID
    title: str
    course_title: str
    state: Literal["draft", "published", "closed"]
    created_at: datetime


class Dashboard(BaseModel):
    counts: Counts
    recent_assessments: list[AssessmentSummary]

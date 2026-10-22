from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ..rag.schemas import Source

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    stem: str = Field(min_length=10, max_length=350)
    options: list[ShortText] = Field(min_length=4, max_length=4)
    correct_option: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=10, max_length=600)
    citation: str = Field(pattern=r"^S[1-8]$")
    evidence_quote: str = Field(min_length=5, max_length=300)

    @field_validator("stem", "explanation", "evidence_quote")
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("Nonblank text without null characters is required")
        return value

    @field_validator("options")
    @classmethod
    def distinct(cls, value):
        if len({" ".join(item.lower().split()) for item in value}) != 4:
            raise ValueError("Four distinct options are required")
        return value


class Generated(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["draft", "insufficient_evidence"]
    question: Candidate | None

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "draft") != (self.question is not None):
            raise ValueError("Question must match status")
        return self


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    material_ids: list[UUID] = Field(min_length=1, max_length=3)
    topic: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=2, max_length=100, pattern=r"^[^\x00-\x1f\x7f]+$"
        ),
    ]
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    cognitive_level: Literal["remember", "understand"] = "understand"
    idempotency_key: UUID
    batch_id: UUID | None = None
    batch_count: int | None = Field(default=None, ge=10, le=30)
    batch_index: int = Field(default=0, ge=0, le=29)

    @model_validator(mode="after")
    def batch_consistent(self):
        if self.batch_count is None:
            if self.batch_id is not None or self.batch_index != 0:
                raise ValueError("Batch metadata must be supplied together")
        elif self.batch_id is None or self.batch_index >= self.batch_count:
            raise ValueError("Question index must be inside a 10–30 question batch")
        return self

    @field_validator("material_ids")
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Choose distinct materials")
        return value


class Readiness(BaseModel):
    mode: Literal["mock", "disabled", "ollama"]
    ready: bool
    hardware: dict
    selection_status: Literal["Hardware-validated model selection: pending"]
    model: str
    error_code: str | None


class DraftSummary(BaseModel):
    id: UUID
    topic: str
    stem: str
    mode: Literal["mock", "ollama"]
    created_at: datetime


class Draft(DraftSummary):
    options: list[str]
    correct_option: int
    explanation: str
    difficulty: Literal["easy", "medium", "hard"]
    cognitive_level: Literal["remember", "understand"]
    status: Literal["unverified"]
    model: str
    retrieval: Literal["keyword_test", "semantic"]
    source: Source
    evidence_quote: str


class DraftPage(BaseModel):
    items: list[DraftSummary]
    total: int
    offset: int
    limit: int

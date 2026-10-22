from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..verifier.schemas import Check


class ValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID


class MathRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    stem: str = Field(min_length=1, max_length=350)
    options: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        min_length=4, max_length=4
    )
    correct_option: int = Field(ge=0, le=3)


class MathResult(BaseModel):
    status: Literal["pass", "fail", "unsupported", "not_applicable"]
    computed: str | None
    matching_options: list[int]
    detail: str


class MathPreview(BaseModel):
    result: MathResult
    saved: Literal[False] = False
    publication_eligible: Literal[False] = False


class DuplicateMatch(BaseModel):
    version_id: UUID
    kind: Literal["exact", "near"]
    similarity: float


class Duplicates(BaseModel):
    status: Literal["pass", "fail", "incomplete"]
    complete: bool
    scanned: int
    match_count: int
    matches: list[DuplicateMatch]
    detail: str


class Report(BaseModel):
    id: UUID
    version_id: UUID
    created_at: datetime
    policy_version: str
    technical_pass: bool
    publication_eligible: Literal[False]
    checks: list[Check]
    math: MathResult
    duplicates: Duplicates
    blockers: list[str]


class History(BaseModel):
    items: list[Report]
    total: int
    offset: int
    limit: int

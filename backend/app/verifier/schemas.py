from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID


class BlindAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answerable: bool
    selected_option: int | None = Field(ge=0, le=3)
    evidence_quote: str = Field(max_length=240)
    reason: str = Field(min_length=5, max_length=240)

    @model_validator(mode="after")
    def consistent(self):
        if self.answerable != (self.selected_option is not None):
            raise ValueError("Answerability must match the selected option")
        if self.answerable and len(self.evidence_quote.strip()) < 5:
            raise ValueError("An answer requires a source quotation")
        return self


Rating = Literal["acceptable", "issue", "uncertain"]


class Critique(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    factual_correctness: Rating
    clarity: Rating
    distractors: Rating
    explanation: Rating
    difficulty: Rating
    reason: str = Field(min_length=5, max_length=400)


class Check(BaseModel):
    name: str
    outcome: Literal["pass", "fail", "acceptable", "issue", "uncertain", "not_evaluated"]
    detail: str


class Report(BaseModel):
    id: UUID
    version_id: UUID
    mode: Literal["mock", "ollama"]
    recommendation: Literal["NOT_EVALUATED", "PASS", "REGENERATE", "REJECT"]
    publication_eligible: Literal[False] = False
    created_at: datetime
    checks: list[Check]
    ai_executed: bool
    blind_option: int | None
    reason: str
    model: str
    model_relationship: Literal["not_evaluated", "same_checkpoint", "different_checkpoint"]
    pending: list[str]


class History(BaseModel):
    items: list[Report]
    total: int
    offset: int
    limit: int


class Readiness(BaseModel):
    mode: Literal["mock", "disabled", "ollama"]
    ready: bool
    model: str
    configured_same_model: bool
    selection_status: Literal["Hardware-validated model selection: pending"]
    error_code: str | None

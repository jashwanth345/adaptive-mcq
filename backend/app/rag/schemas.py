from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=2, max_length=500, pattern=r"^[^\x00-\x1f\x7f]+$"
        ),
    ]
    material_ids: list[UUID] = Field(min_length=1, max_length=5)

    @field_validator("material_ids")
    @classmethod
    def unique_materials(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Select each material once")
        return value


class IndexStatus(BaseModel):
    material_id: UUID
    chunks: int
    indexed: int
    state: Literal["not_indexed", "partial", "ready"]
    model_available: bool
    model: str
    revision: str


class Source(BaseModel):
    citation: str
    material_id: UUID
    title: str
    document_id: UUID
    chunk_id: UUID
    page_start: int
    page_end: int
    similarity: float
    content_sha256: str
    excerpt_sha256: str
    excerpt: str
    clipped: bool


class SearchResponse(BaseModel):
    status: Literal["sources_found", "insufficient_evidence"]
    sources: list[Source]
    excerpt_char_count: int
    excerpt_char_limit: int
    model: str
    revision: str
    threshold: float

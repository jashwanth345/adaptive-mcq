from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

Title = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=250, pattern=r"^[^\x00-\x1f\x7f]+$"
    ),
]


class Material(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    page_count: int
    byte_size: int
    chunk_count: int


class MaterialPage(BaseModel):
    items: list[Material]
    total: int
    offset: int
    limit: int


class Chunk(BaseModel):
    ordinal: int
    content: str


class Preview(Material):
    page: int
    chunks: list[Chunk]
    empty_pages: list[int]
    ocr_pages: list[int] = Field(default_factory=list)


class Uploaded(BaseModel):
    id: UUID
    reused: bool

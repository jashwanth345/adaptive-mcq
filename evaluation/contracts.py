"""Bounded, explicit experiment inputs. Files are data, never executable instructions."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def digest(value):
    raw = (
        value
        if isinstance(value, str)
        else json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Document(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    revision: str = Field(min_length=1, max_length=100)
    split: Literal["development", "test"]
    text: str = Field(min_length=10, max_length=12000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def integrity(self):
        if digest(self.text) != self.sha256:
            raise ValueError("Document hash mismatch")
        return self


class Context(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    text: str = Field(min_length=5, max_length=1500)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class Case(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    document_id: str
    topic: str = Field(min_length=2, max_length=100)
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    cognitive_level: Literal["remember", "understand", "apply"] = "understand"
    question_type: Literal["conceptual", "numerical"] = "conceptual"
    contexts: list[Context] = Field(min_length=1, max_length=3)
    retrieval: Literal["synthetic", "frozen_local_rag"]
    embedding_model: str = Field(min_length=1, max_length=150)
    embedding_revision: str = Field(min_length=1, max_length=150)


class Dataset(Strict):
    version: Literal["evaluation-dataset-v1"] = "evaluation-dataset-v1"
    name: str = Field(min_length=1, max_length=100)
    synthetic: bool
    authorized_material: Literal[True]
    documents: list[Document] = Field(min_length=1, max_length=50)
    cases: list[Case] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def consistent(self):
        docs = {d.id: d for d in self.documents}
        if len(docs) != len(self.documents) or len({c.id for c in self.cases}) != len(
            self.cases
        ):
            raise ValueError("Duplicate document or case ID")
        hashes = {}
        for doc in self.documents:
            # Whitespace changes do not make duplicate source content a new held-out split.
            key = digest(" ".join(doc.text.split()).casefold())
            if key in hashes:
                raise ValueError(
                    "Duplicate source content, including cross-split overlap"
                )
            hashes[key] = doc.split
        for case in self.cases:
            if case.document_id not in docs or len(
                {c.id for c in case.contexts}
            ) != len(case.contexts):
                raise ValueError("Missing document or duplicate context ID")
            for context in case.contexts:
                if (
                    digest(context.text) != context.sha256
                    or context.text not in docs[case.document_id].text
                ):
                    raise ValueError(
                        "Retrieved context does not match its frozen document"
                    )
            if not self.synthetic and case.retrieval != "frozen_local_rag":
                raise ValueError(
                    "Real datasets require frozen local retrieval provenance"
                )
        return self


class Pair(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    generator: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{1,120}$")
    verifier: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{1,120}$")


class Config(Strict):
    version: Literal["matched-ablation-v1"] = "matched-ablation-v1"
    mode: Literal["mock", "local"] = "mock"
    development_source_hashes: list[str] = Field(default_factory=list, max_length=50)
    split: Literal["development", "test"] = "development"
    seeds: list[int] = Field(default_factory=lambda: [42], min_length=1, max_length=5)
    pairs: list[Pair] = Field(min_length=1, max_length=3)
    context_tokens: int = Field(default=2048, ge=512, le=2048)
    output_tokens: int = Field(default=512, ge=64, le=512)
    frozen_protocol_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def bounded(self):
        import re

        if any(
            not re.fullmatch(r"[a-f0-9]{64}", value)
            for value in self.development_source_hashes
        ):
            raise ValueError("Invalid development source hash")
        if len(set(self.seeds)) != len(self.seeds) or any(
            s < 0 or s > 2147483647 for s in self.seeds
        ):
            raise ValueError("Seeds must be unique bounded nonnegative integers")
        if (
            len({p.id for p in self.pairs}) != len(self.pairs)
            or self.output_tokens >= self.context_tokens
        ):
            raise ValueError("Duplicate pair ID or invalid token budget")
        return self


class Question(Strict):
    stem: str = Field(min_length=5, max_length=350)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=5, max_length=600)
    citation: str | None = Field(default=None, pattern=r"^S[1-3]$")
    evidence_quote: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def distinct(self):
        if any(not x.strip() or len(x) > 150 or "\x00" in x for x in self.options):
            raise ValueError("Invalid option")
        if len({" ".join(x.casefold().split()) for x in self.options}) != 4:
            raise ValueError("Options must be distinct")
        return self


class Generated(Strict):
    status: Literal["draft", "insufficient_evidence"]
    question: Question | None

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "draft") != (self.question is not None):
            raise ValueError("Status and question disagree")
        return self

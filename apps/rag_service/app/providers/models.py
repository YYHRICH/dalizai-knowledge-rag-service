from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    model: str
    dimension: int
    embeddings: list[list[float]]
    usage: dict | None = None


@dataclass(frozen=True)
class RerankDocument:
    id: str
    text: str


@dataclass(frozen=True)
class RerankResult:
    id: str
    index: int
    score: float

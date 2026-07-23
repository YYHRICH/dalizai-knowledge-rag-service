from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RagStatus = Literal["success", "low_confidence", "not_found", "error"]


class RagFilters(BaseModel):
    businessDomains: list[str] | None = None
    knowledgeTypes: list[str] | None = None
    effectiveOnly: bool = True
    cityCode: str | None = None
    stationId: str | None = None


class RagQueryRequest(BaseModel):
    requestId: str
    traceId: str
    sessionId: str
    userId: str | None = None
    channel: str = "wechat_mini_program"
    originalQuery: str | None = None
    query: str
    normalizedQueryHint: str | None = None
    intent: str | None = None
    subIntent: str | None = None
    topK: int | None = Field(default=None, ge=1)
    filters: RagFilters = Field(default_factory=RagFilters)
    context: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSource(BaseModel):
    docId: str | None = None
    docTitle: str | None = None
    section: str | None = None
    updatedAt: str | None = None


class KnowledgeItemResponse(BaseModel):
    knowledgeId: str
    chunkId: str
    title: str
    businessDomain: str | None = None
    knowledgeType: str | None = None
    summary: str
    content: str
    score: float
    allowedClaims: list[str]
    forbiddenClaims: list[str] = Field(default_factory=list)
    source: KnowledgeSource
    cards: list[dict[str, Any]] = Field(default_factory=list)


class RagFallback(BaseModel):
    reason: str
    suggestedAction: str


class RagError(BaseModel):
    code: str
    message: str
    retryable: bool


class RagQueryResponse(BaseModel):
    requestId: str
    traceId: str
    status: RagStatus
    answerable: bool
    confidence: float
    queryRewrite: str | None = None
    knowledgeVersion: str | None = None
    items: list[KnowledgeItemResponse] = Field(default_factory=list)
    fallback: RagFallback | None = None
    error: RagError | None = None
    latencyMs: int | None = None

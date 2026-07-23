from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from apps.rag_service.app.schemas.rag import RagFilters, RagQueryResponse

EvalCaseSource = Literal["knowledge", "agent"]


class EvalCaseResponse(BaseModel):
    id: str
    query: str
    expectedStatus: str
    shouldCallRag: bool = True
    businessDomains: list[str] = Field(default_factory=list)
    knowledgeTypes: list[str] = Field(default_factory=list)
    expectedKnowledgeId: str | None = None
    expectedContextIds: list[str] = Field(default_factory=list)
    expectedClaims: list[str] = Field(default_factory=list)
    negativeContextIds: list[str] = Field(default_factory=list)
    channel: str = "wechat_mini_program"
    intent: str | None = None
    subIntent: str | None = None
    notes: str | None = None


class EvalCaseListResponse(BaseModel):
    source: EvalCaseSource
    cases: list[EvalCaseResponse]
    count: int


class DebugQueryRequest(BaseModel):
    requestId: str | None = None
    traceId: str | None = None
    sessionId: str = "debug_session"
    userId: str | None = None
    channel: str = "wechat_mini_program"
    originalQuery: str | None = None
    query: str
    intent: str | None = None
    subIntent: str | None = None
    topK: int | None = Field(default=5, ge=1)
    filters: RagFilters = Field(default_factory=RagFilters)
    expectedStatus: str | None = None
    expectedKnowledgeId: str | None = None
    expectedContextIds: list[str] = Field(default_factory=list)
    expectedClaims: list[str] = Field(default_factory=list)
    negativeContextIds: list[str] = Field(default_factory=list)
    referenceAnswer: str | None = None


class DebugQueryEvaluation(BaseModel):
    statusMatch: bool
    expectedContextHit: bool
    contextPrecision: float
    contextRecall: float
    faithfulnessProxy: float
    responseRelevancyProxy: float
    score: float
    passed: bool
    retrievedContextIds: list[str]
    retrievedKnowledgeIds: list[str]


class DebugQueryResponse(BaseModel):
    requestId: str
    traceId: str
    response: RagQueryResponse
    evaluation: DebugQueryEvaluation | None = None

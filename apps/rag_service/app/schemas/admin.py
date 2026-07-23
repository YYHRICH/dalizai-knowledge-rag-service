from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GapHandledStatus = Literal["open", "planned", "resolved", "ignored"]


class KnowledgeGapClusterResponse(BaseModel):
    clusterId: str
    representativeQuery: str
    clusterTitle: str | None = None
    summary: str | None = None
    businessDomainGuess: str | None = None
    knowledgeTypeGuess: str | None = None
    ownerTeam: str | None = None
    eventCount: int
    statusBreakdown: dict[str, int] = Field(default_factory=dict)
    topCandidateKnowledgeIds: list[str] = Field(default_factory=list)
    queryExamples: list[str] = Field(default_factory=list)
    handledStatus: GapHandledStatus
    firstSeenAt: str
    lastSeenAt: str
    createdAt: str | None = None
    updatedAt: str | None = None


class KnowledgeGapListResponse(BaseModel):
    clusters: list[KnowledgeGapClusterResponse]
    count: int


class UpdateKnowledgeGapStatusRequest(BaseModel):
    handledStatus: GapHandledStatus
    handledBy: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=500)


class UpdateKnowledgeGapStatusResponse(BaseModel):
    actionId: str
    clusterId: str
    handledStatus: GapHandledStatus

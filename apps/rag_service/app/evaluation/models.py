from __future__ import annotations

from dataclasses import dataclass, field

from apps.rag_service.app.schemas.rag import RagQueryResponse


@dataclass(frozen=True)
class RagEvalCase:
    id: str
    query: str
    expected_status: str
    should_call_rag: bool = True
    business_domains: list[str] = field(default_factory=list)
    knowledge_types: list[str] = field(default_factory=list)
    expected_context_ids: list[str] = field(default_factory=list)
    expected_knowledge_id: str | None = None
    reference_answer: str | None = None
    expected_claims: list[str] = field(default_factory=list)
    negative_context_ids: list[str] = field(default_factory=list)
    channel: str = "wechat_mini_program"
    intent: str | None = None
    sub_intent: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RagEvalCaseResult:
    case: RagEvalCase
    response: RagQueryResponse
    status_match: bool
    expected_context_hit: bool
    context_precision: float
    context_recall: float
    faithfulness_proxy: float
    response_relevancy_proxy: float
    score: float
    retrieved_context_ids: list[str]
    retrieved_knowledge_ids: list[str]

    @property
    def passed(self) -> bool:
        return self.status_match and self.expected_context_hit and self.score >= 0.75


@dataclass(frozen=True)
class RagEvalSummary:
    total: int
    passed: int
    failed: int
    status_accuracy: float
    expected_context_hit_rate: float
    context_precision: float
    context_recall: float
    faithfulness_proxy: float
    response_relevancy_proxy: float
    mean_score: float


@dataclass(frozen=True)
class RagEvalReport:
    summary: RagEvalSummary
    results: list[RagEvalCaseResult]

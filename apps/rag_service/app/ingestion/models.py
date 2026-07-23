from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

IssueLevel = Literal["error", "warning"]


@dataclass(frozen=True)
class EvalQuestion:
    question: str
    reference_answer: str
    expected_context_ids: list[str]
    expected_status: str
    expected_claims: list[str]
    negative_context_ids: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass(frozen=True)
class KnowledgeDocument:
    path: Path
    metadata: dict[str, Any]
    title: str | None
    items: list[KnowledgeItem]


@dataclass(frozen=True)
class KnowledgeItem:
    knowledge_id: str
    chunk_id: str
    title: str
    summary: str
    content: str
    allowed_claims: list[str]
    forbidden_claims: list[str]
    keywords: list[str]
    similar_questions: list[str]
    eval_questions: list[EvalQuestion]
    source_path: Path
    document_metadata: dict[str, Any]

    @property
    def business_domain(self) -> str | None:
        value = self.document_metadata.get("businessDomain")
        return str(value) if value is not None else None

    @property
    def knowledge_type(self) -> str | None:
        value = self.document_metadata.get("knowledgeType")
        return str(value) if value is not None else None

    @property
    def risk_level(self) -> str:
        value = self.document_metadata.get("riskLevel") or "medium"
        return str(value)


@dataclass(frozen=True)
class ValidationIssue:
    level: IssueLevel
    path: Path
    message: str
    knowledge_id: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    documents: list[KnowledgeDocument]
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def item_count(self) -> int:
        return sum(len(document.items) for document in self.documents)

    @property
    def ok(self) -> bool:
        return not self.errors

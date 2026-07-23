from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import KnowledgeDocument, KnowledgeItem, ValidationIssue, ValidationReport

BUSINESS_DOMAINS = {
    "charging",
    "device",
    "station",
    "payment",
    "coupon",
    "refund",
    "invoice",
    "account",
    "order",
    "customer_service",
    "general",
}

KNOWLEDGE_TYPES = {
    "faq",
    "operation_guide",
    "billing_policy",
    "coupon_policy",
    "refund_policy",
    "troubleshooting",
    "handoff_guide",
    "service_rule",
    "risk_notice",
}

RISK_LEVELS = {"low", "medium", "high", "critical"}
STATUSES = {"draft", "reviewing", "active", "disabled", "expired", "archived"}
REQUIRED_METADATA = {
    "docId",
    "docTitle",
    "businessDomain",
    "knowledgeType",
    "status",
    "ownerTeam",
    "effectiveFrom",
    "updatedAt",
    "reviewDueAt",
}
KNOWLEDGE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*[0-9]{3}$")
HIGH_RISK_TYPES = {"billing_policy", "refund_policy", "coupon_policy", "risk_notice"}


@dataclass(frozen=True)
class ValidationOptions:
    require_eval_questions: bool = False


class KnowledgeValidator:
    def validate(
        self,
        documents: list[KnowledgeDocument],
        parser_issues: list[ValidationIssue] | None = None,
        options: ValidationOptions | None = None,
    ) -> ValidationReport:
        opts = options or ValidationOptions()
        issues = list(parser_issues or [])
        seen_knowledge_ids: set[str] = set()

        for document in documents:
            self._validate_document_metadata(document, issues)
            for item in document.items:
                self._validate_item(item, seen_knowledge_ids, issues, opts)

        return ValidationReport(documents, issues)

    def _validate_document_metadata(
        self,
        document: KnowledgeDocument,
        issues: list[ValidationIssue],
    ) -> None:
        metadata = document.metadata
        for field in sorted(REQUIRED_METADATA):
            if self._is_empty(metadata.get(field)):
                issues.append(ValidationIssue("error", document.path, f"missing metadata: {field}"))

        business_domain = metadata.get("businessDomain")
        if not self._is_empty(business_domain) and str(business_domain) not in BUSINESS_DOMAINS:
            issues.append(
                ValidationIssue("error", document.path, f"invalid businessDomain: {business_domain}")
            )

        knowledge_type = metadata.get("knowledgeType")
        if not self._is_empty(knowledge_type) and str(knowledge_type) not in KNOWLEDGE_TYPES:
            issues.append(
                ValidationIssue("error", document.path, f"invalid knowledgeType: {knowledge_type}")
            )

        status = metadata.get("status")
        if not self._is_empty(status) and str(status) not in STATUSES:
            issues.append(ValidationIssue("error", document.path, f"invalid status: {status}"))

        risk_level = self._risk_level(metadata)
        if risk_level not in RISK_LEVELS:
            issues.append(ValidationIssue("error", document.path, f"invalid riskLevel: {risk_level}"))
        if risk_level == "critical" and str(status) == "active":
            issues.append(
                ValidationIssue(
                    "error",
                    document.path,
                    "riskLevel=critical active knowledge is not allowed in v1",
                )
            )

        for field in ["effectiveFrom", "effectiveTo", "updatedAt", "reviewDueAt"]:
            if not self._is_empty(metadata.get(field)) and self._parse_datetime(metadata[field]) is None:
                issues.append(ValidationIssue("error", document.path, f"invalid datetime: {field}"))

    def _validate_item(
        self,
        item: KnowledgeItem,
        seen_knowledge_ids: set[str],
        issues: list[ValidationIssue],
        options: ValidationOptions,
    ) -> None:
        if item.knowledge_id in seen_knowledge_ids:
            issues.append(
                ValidationIssue("error", item.source_path, "duplicate knowledgeId", item.knowledge_id)
            )
        seen_knowledge_ids.add(item.knowledge_id)

        if not KNOWLEDGE_ID_RE.match(item.knowledge_id):
            issues.append(
                ValidationIssue(
                    "error",
                    item.source_path,
                    "invalid knowledgeId format",
                    item.knowledge_id,
                )
            )
        if not item.title:
            issues.append(ValidationIssue("error", item.source_path, "missing title", item.knowledge_id))
        if not item.summary:
            issues.append(ValidationIssue("error", item.source_path, "missing Summary", item.knowledge_id))
        elif len(item.summary) > 120:
            issues.append(
                ValidationIssue("error", item.source_path, "Summary exceeds 120 chars", item.knowledge_id)
            )
        if not item.content:
            issues.append(ValidationIssue("error", item.source_path, "missing Content", item.knowledge_id))
        elif len(item.content) > 3000:
            issues.append(
                ValidationIssue("error", item.source_path, "Content exceeds 3000 chars", item.knowledge_id)
            )
        elif len(item.content) > 1500:
            issues.append(
                ValidationIssue(
                    "warning",
                    item.source_path,
                    "Content exceeds recommended 1500 chars",
                    item.knowledge_id,
                )
            )
        if not item.allowed_claims:
            issues.append(
                ValidationIssue("error", item.source_path, "missing Allowed Claims", item.knowledge_id)
            )

        risk_level = self._risk_level(item.document_metadata)
        if risk_level == "high" and not item.forbidden_claims:
            issues.append(
                ValidationIssue(
                    "error",
                    item.source_path,
                    "high risk item requires Forbidden Claims",
                    item.knowledge_id,
                )
            )
        elif risk_level in {"low", "medium"} and not item.forbidden_claims:
            issues.append(
                ValidationIssue(
                    "warning",
                    item.source_path,
                    "Forbidden Claims is empty",
                    item.knowledge_id,
                )
            )

        if len(item.keywords) < 2:
            issues.append(
                ValidationIssue(
                    "warning",
                    item.source_path,
                    "Keywords should contain at least 2 items",
                    item.knowledge_id,
                )
            )
        if item.knowledge_type == "faq" and len(item.similar_questions) < 2:
            issues.append(
                ValidationIssue(
                    "warning",
                    item.source_path,
                    "FAQ Similar Questions should contain at least 2 items",
                    item.knowledge_id,
                )
            )
        if options.require_eval_questions and not item.eval_questions:
            issues.append(
                ValidationIssue("error", item.source_path, "missing Eval Questions", item.knowledge_id)
            )
        for eval_question in item.eval_questions:
            self._validate_eval_question(item, eval_question, issues)

    def _validate_eval_question(
        self,
        item: KnowledgeItem,
        eval_question: Any,
        issues: list[ValidationIssue],
    ) -> None:
        if not eval_question.question:
            issues.append(
                ValidationIssue("error", item.source_path, "Eval question is empty", item.knowledge_id)
            )
        if not eval_question.reference_answer:
            issues.append(
                ValidationIssue(
                    "error",
                    item.source_path,
                    "Eval referenceAnswer is empty",
                    item.knowledge_id,
                )
            )
        if not eval_question.expected_context_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    item.source_path,
                    "Eval expectedContextIds is empty",
                    item.knowledge_id,
                )
            )
        if not eval_question.expected_status:
            issues.append(
                ValidationIssue(
                    "error",
                    item.source_path,
                    "Eval expectedStatus is empty",
                    item.knowledge_id,
                )
            )
        if not eval_question.expected_claims:
            issues.append(
                ValidationIssue(
                    "error",
                    item.source_path,
                    "Eval expectedClaims is empty",
                    item.knowledge_id,
                )
            )

    def _risk_level(self, metadata: dict[str, Any]) -> str:
        risk_level = metadata.get("riskLevel")
        if not self._is_empty(risk_level):
            return str(risk_level)
        knowledge_type = str(metadata.get("knowledgeType") or "")
        return "high" if knowledge_type in HIGH_RISK_TYPES else "medium"

    def _is_empty(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

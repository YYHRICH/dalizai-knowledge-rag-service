from __future__ import annotations

import json
from pathlib import Path

from apps.rag_service.app.evaluation.models import RagEvalCase
from apps.rag_service.app.ingestion import KnowledgeMarkdownParser


def load_eval_cases_from_knowledge(knowledge_dir: Path | str) -> list[RagEvalCase]:
    documents, issues = KnowledgeMarkdownParser().parse_directory(knowledge_dir)
    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        messages = "; ".join(f"{issue.path}: {issue.message}" for issue in errors[:5])
        raise ValueError(f"Cannot load eval cases from invalid knowledge: {messages}")

    cases: list[RagEvalCase] = []
    seen_ids: set[str] = set()
    for document in documents:
        for item in document.items:
            business_domain = item.business_domain
            knowledge_type = item.knowledge_type
            for index, eval_question in enumerate(item.eval_questions, start=1):
                case_id = f"{item.knowledge_id}__eval_{index:02d}"
                if case_id in seen_ids:
                    raise ValueError(f"Duplicate eval case id: {case_id}")
                seen_ids.add(case_id)
                cases.append(
                    RagEvalCase(
                        id=case_id,
                        query=eval_question.question,
                        expected_status=eval_question.expected_status,
                        business_domains=[business_domain] if business_domain else [],
                        knowledge_types=[knowledge_type] if knowledge_type else [],
                        expected_context_ids=eval_question.expected_context_ids,
                        expected_knowledge_id=item.knowledge_id,
                        reference_answer=eval_question.reference_answer,
                        expected_claims=eval_question.expected_claims,
                        negative_context_ids=eval_question.negative_context_ids,
                        notes=eval_question.notes,
                    )
                )
    return cases


def load_eval_cases_from_jsonl(path: Path | str) -> list[RagEvalCase]:
    cases: list[RagEvalCase] = []
    seen_ids: set[str] = set()
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        raw = json.loads(stripped)
        case_id = str(raw.get("id") or f"case_{line_no:04d}")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate eval case id: {case_id}")
        seen_ids.add(case_id)
        filters = raw.get("filters") or {}
        expected_knowledge_id = raw.get("expectedKnowledgeId")
        expected_context_ids = raw.get("expectedContextIds") or []
        if not expected_context_ids and expected_knowledge_id:
            expected_context_ids = [f"{expected_knowledge_id}#main"]
        cases.append(
            RagEvalCase(
                id=case_id,
                query=str(raw.get("query") or raw.get("question") or ""),
                expected_status=str(raw.get("expectedStatus") or ""),
                business_domains=list(raw.get("businessDomains") or filters.get("businessDomains") or []),
                knowledge_types=list(raw.get("knowledgeTypes") or filters.get("knowledgeTypes") or []),
                expected_context_ids=list(expected_context_ids),
                expected_knowledge_id=expected_knowledge_id,
                reference_answer=raw.get("referenceAnswer"),
                expected_claims=list(raw.get("expectedClaims") or []),
                negative_context_ids=list(raw.get("negativeContextIds") or []),
                channel=str(raw.get("channel") or "wechat_mini_program"),
                intent=raw.get("intent"),
                sub_intent=raw.get("subIntent"),
                notes=raw.get("notes"),
            )
        )
    return cases

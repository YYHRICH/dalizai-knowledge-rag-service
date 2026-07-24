"""评测用例加载器。

从两个来源加载评测用例：
1. 知识库 Markdown 文件的内嵌 Eval Questions（``load_eval_cases_from_knowledge``）。
2. 独立的 ``eval/agent_cases.jsonl`` 文件（``load_eval_cases_from_jsonl``）。
"""

from __future__ import annotations

import json
from pathlib import Path

from apps.rag_service.app.evaluation.models import RagEvalCase
from apps.rag_service.app.ingestion import KnowledgeMarkdownParser


def load_eval_cases_from_knowledge(knowledge_dir: Path | str) -> list[RagEvalCase]:
    """从知识库 Markdown 文件中加载评测用例。

    解析所有 .md 文件，收集每个条目的 Eval Questions，
    case_id 格式为 ``{knowledgeId}__eval_{NN}``。

    Args:
        knowledge_dir: 知识库根目录。

    Returns:
        评测用例列表。

    Raises:
        ValueError: 知识库有解析错误或 case_id 重复。
    """
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
                should_call_rag=True,
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
    """从 JSONL 文件加载评测用例。

    每行一个 JSON 对象，支持 agent_cases.jsonl 格式。
    自动补全 expectedContextIds（如果没有但 expectedKnowledgeId 存在，
    则生成 ``{expectedKnowledgeId}#main``）。

    Args:
        path: JSONL 文件路径。

    Returns:
        评测用例列表。

    Raises:
        ValueError: case_id 重复。
    """
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
                should_call_rag=bool(raw.get("shouldCallRag", True)),
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

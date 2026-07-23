from __future__ import annotations

from statistics import mean

from apps.rag_service.app.evaluation.models import (
    RagEvalCase,
    RagEvalCaseResult,
    RagEvalReport,
    RagEvalSummary,
)
from apps.rag_service.app.schemas.rag import RagFilters, RagQueryRequest, RagQueryResponse


class RagEvaluator:
    def __init__(self, query_service) -> None:
        self.query_service = query_service

    def evaluate(self, cases: list[RagEvalCase]) -> RagEvalReport:
        results = [self.evaluate_case(case) for case in cases]
        return RagEvalReport(summary=self._summary(results), results=results)

    def evaluate_case(self, case: RagEvalCase) -> RagEvalCaseResult:
        response = self.query_service.query(
            RagQueryRequest(
                requestId=f"eval_{case.id}",
                traceId=f"eval_trace_{case.id}",
                sessionId="eval_session",
                channel=case.channel,
                query=case.query,
                intent=case.intent,
                subIntent=case.sub_intent,
                filters=RagFilters(
                    businessDomains=case.business_domains or None,
                    knowledgeTypes=case.knowledge_types or None,
                ),
            )
        )
        return score_case(case, response)

    def _summary(self, results: list[RagEvalCaseResult]) -> RagEvalSummary:
        if not results:
            return RagEvalSummary(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        return RagEvalSummary(
            total=len(results),
            passed=sum(1 for result in results if result.passed),
            failed=sum(1 for result in results if not result.passed),
            status_accuracy=mean(float(result.status_match) for result in results),
            expected_context_hit_rate=mean(float(result.expected_context_hit) for result in results),
            context_precision=mean(result.context_precision for result in results),
            context_recall=mean(result.context_recall for result in results),
            faithfulness_proxy=mean(result.faithfulness_proxy for result in results),
            response_relevancy_proxy=mean(result.response_relevancy_proxy for result in results),
            mean_score=mean(result.score for result in results),
        )


def score_case(case: RagEvalCase, response: RagQueryResponse) -> RagEvalCaseResult:
    retrieved_context_ids = [item.chunkId for item in response.items]
    retrieved_knowledge_ids = [item.knowledgeId for item in response.items]
    expected_context_ids = case.expected_context_ids
    status_match = response.status == case.expected_status
    expected_context_hit = _expected_context_hit(case, response)
    context_precision = _context_precision(retrieved_context_ids, expected_context_ids, case.negative_context_ids)
    context_recall = _context_recall(retrieved_context_ids, expected_context_ids)
    faithfulness_proxy = _faithfulness_proxy(case, response)
    response_relevancy_proxy = _response_relevancy_proxy(case, response, expected_context_hit)
    score = (
        0.20 * float(status_match)
        + 0.25 * context_precision
        + 0.25 * context_recall
        + 0.15 * faithfulness_proxy
        + 0.15 * response_relevancy_proxy
    )
    return RagEvalCaseResult(
        case=case,
        response=response,
        status_match=status_match,
        expected_context_hit=expected_context_hit,
        context_precision=context_precision,
        context_recall=context_recall,
        faithfulness_proxy=faithfulness_proxy,
        response_relevancy_proxy=response_relevancy_proxy,
        score=score,
        retrieved_context_ids=retrieved_context_ids,
        retrieved_knowledge_ids=retrieved_knowledge_ids,
    )


def _expected_context_hit(case: RagEvalCase, response: RagQueryResponse) -> bool:
    if case.expected_status == "not_found":
        return not response.items
    if case.expected_context_ids:
        return any(item.chunkId in case.expected_context_ids for item in response.items)
    if case.expected_knowledge_id:
        return any(item.knowledgeId == case.expected_knowledge_id for item in response.items)
    return response.status == case.expected_status


def _context_precision(
    retrieved_context_ids: list[str],
    expected_context_ids: list[str],
    negative_context_ids: list[str],
) -> float:
    if not expected_context_ids:
        return 1.0 if not retrieved_context_ids else 0.0
    if not retrieved_context_ids:
        return 0.0
    expected = set(expected_context_ids)
    negative = set(negative_context_ids)
    hits = 0
    precision_sum = 0.0
    for rank, context_id in enumerate(retrieved_context_ids, start=1):
        if context_id in negative:
            continue
        if context_id in expected:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / len(expected)


def _context_recall(retrieved_context_ids: list[str], expected_context_ids: list[str]) -> float:
    if not expected_context_ids:
        return 1.0 if not retrieved_context_ids else 0.0
    return len(set(retrieved_context_ids) & set(expected_context_ids)) / len(set(expected_context_ids))


def _faithfulness_proxy(case: RagEvalCase, response: RagQueryResponse) -> float:
    if case.expected_status == "not_found":
        return 1.0 if not response.items else 0.0
    if not case.expected_claims:
        return 1.0 if response.items else 0.0
    support_text = "\n".join(
        [
            item.summary
            + "\n"
            + item.content
            + "\n"
            + "\n".join(item.allowedClaims)
            for item in response.items
        ]
    )
    if not support_text:
        return 0.0
    covered = sum(1 for claim in case.expected_claims if _contains_loose(support_text, claim))
    return covered / len(case.expected_claims)


def _response_relevancy_proxy(
    case: RagEvalCase,
    response: RagQueryResponse,
    expected_context_hit: bool,
) -> float:
    if case.expected_status == "not_found":
        return 1.0 if response.status == "not_found" and not response.items else 0.0
    if response.status != "success":
        return 0.0
    if case.reference_answer:
        returned_text = "\n".join(
            item.summary + "\n" + item.content + "\n" + "\n".join(item.allowedClaims)
            for item in response.items
        )
        answer_terms = _content_terms(case.reference_answer)
        if answer_terms:
            term_hit_rate = sum(1 for term in answer_terms if term in returned_text) / len(answer_terms)
            return max(term_hit_rate, float(expected_context_hit))
    return 1.0 if expected_context_hit else 0.0


def _contains_loose(text: str, claim: str) -> bool:
    if claim in text:
        return True
    terms = _content_terms(claim)
    if not terms:
        return False
    return sum(1 for term in terms if term in text) / len(terms) >= 0.6


def _content_terms(text: str) -> list[str]:
    separators = "，。；、,.!?！？;：:（）()\n\t "
    normalized = text
    for separator in separators:
        normalized = normalized.replace(separator, "|")
    return [part for part in normalized.split("|") if len(part) >= 2]

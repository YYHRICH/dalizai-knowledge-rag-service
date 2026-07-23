from apps.rag_service.app.evaluation.evaluator import RagEvaluator, score_case
from apps.rag_service.app.evaluation.models import RagEvalCase
from apps.rag_service.app.evaluation.reporting import report_to_dict
from apps.rag_service.app.schemas.rag import KnowledgeItemResponse, KnowledgeSource, RagQueryResponse


def response(status="success", items=None):
    return RagQueryResponse(
        requestId="request_eval",
        traceId="trace_eval",
        status=status,
        answerable=status == "success",
        confidence=0.9 if status == "success" else 0.0,
        items=items or [],
        latencyMs=10,
    )


def item(chunk_id="faq_charge_scan_001#main", knowledge_id="faq_charge_scan_001"):
    return KnowledgeItemResponse(
        knowledgeId=knowledge_id,
        chunkId=chunk_id,
        title="怎么扫码充电？",
        summary="用户连接充电枪后，可以通过小程序扫码启动充电。",
        content="余额不足或设备不可用时，系统会在启动前提示。",
        score=0.93,
        allowedClaims=[
            "用户连接充电枪后，可以在小程序中扫码启动充电。",
            "余额不足或设备不可用时，系统会在启动前提示。",
        ],
        forbiddenClaims=[],
        source=KnowledgeSource(docId="doc_charging_faq_v1"),
    )


def test_score_case_success_with_expected_context() -> None:
    case = RagEvalCase(
        id="case_001",
        query="怎么扫码充电？",
        expected_status="success",
        expected_context_ids=["faq_charge_scan_001#main"],
        expected_claims=["用户连接充电枪后，可以在小程序中扫码启动充电。"],
        reference_answer="用户连接充电枪后，可以在小程序中扫码启动充电。",
    )

    result = score_case(case, response(items=[item()]))

    assert result.status_match is True
    assert result.expected_context_hit is True
    assert result.context_precision == 1.0
    assert result.context_recall == 1.0
    assert result.faithfulness_proxy == 1.0
    assert result.response_relevancy_proxy == 1.0
    assert result.passed is True


def test_score_case_not_found_expected() -> None:
    case = RagEvalCase(id="case_002", query="有没有火星优惠？", expected_status="not_found")

    result = score_case(case, response(status="not_found"))

    assert result.status_match is True
    assert result.expected_context_hit is True
    assert result.context_precision == 1.0
    assert result.context_recall == 1.0
    assert result.passed is True


class FakeQueryService:
    def query(self, request):
        assert request.query == "怎么扫码充电？"
        assert request.filters.businessDomains == ["charging"]
        return response(items=[item()])


def test_evaluator_builds_query_request_and_summary() -> None:
    evaluator = RagEvaluator(FakeQueryService())
    case = RagEvalCase(
        id="case_003",
        query="怎么扫码充电？",
        expected_status="success",
        business_domains=["charging"],
        knowledge_types=["faq"],
        expected_context_ids=["faq_charge_scan_001#main"],
    )

    report = evaluator.evaluate([case])

    assert report.summary.total == 1
    assert report.summary.passed == 1
    assert report.summary.mean_score == 1.0
    assert report_to_dict(report)["results"][0]["id"] == "case_003"

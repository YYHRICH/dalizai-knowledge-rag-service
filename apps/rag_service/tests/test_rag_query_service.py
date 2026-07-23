from types import SimpleNamespace

from apps.rag_service.app.providers.models import RerankResult
from apps.rag_service.app.schemas.rag import RagFilters, RagQueryRequest
from apps.rag_service.app.services.rag_query_service import RagQueryService


class FakeEmbeddingClient:
    def embed_texts(self, texts):
        assert texts == ["怎么扫码充电？"]
        return SimpleNamespace(embeddings=[[0.1, 0.2, 0.3]])


class FakeStore:
    def __init__(self, points):
        self.points = points
        self.seen_channel = None

    def search(self, collection_name, query_vector, filters, limit, channel=None):
        self.seen_channel = channel
        assert collection_name == "dalizai_knowledge_v1"
        assert query_vector == [0.1, 0.2, 0.3]
        assert isinstance(filters, RagFilters)
        assert limit == 10
        return self.points


class FakeRerankClient:
    def rerank(self, query, documents, top_n=None):
        assert query == "怎么扫码充电？"
        assert top_n == 5
        return [RerankResult(id="faq_charge_scan_001#main", index=0, score=0.93)]


class FakeRepository:
    def __init__(self):
        self.audit_logs = []
        self.gap_events = []

    def create_audit_log(self, record):
        self.audit_logs.append(record)

    def create_gap_event(self, record):
        self.gap_events.append(record)


def settings():
    return SimpleNamespace(
        rag_default_top_k=5,
        rag_max_top_k=10,
        rerank_top_n=10,
        qdrant_collection_alias="dalizai_knowledge_v1",
        success_confidence_threshold=0.75,
        low_confidence_threshold=0.50,
        rag_service_api_key="test_salt",
    )


def request():
    return RagQueryRequest(
        requestId="request_001",
        traceId="trace_001",
        sessionId="session_001",
        channel="wechat_mini_program",
        query="怎么扫码充电？",
        filters=RagFilters(businessDomains=["charging"], knowledgeTypes=["faq"]),
    )


def service_with(points):
    service = RagQueryService.__new__(RagQueryService)
    service.settings = settings()
    service.embedding_client = FakeEmbeddingClient()
    service.store = FakeStore(points)
    service.rerank_client = FakeRerankClient()
    service.repository = FakeRepository()
    return service


def point(payload):
    return SimpleNamespace(payload=payload, score=0.88)


def test_query_success_response() -> None:
    service = service_with([
        point(
            {
                "knowledgeId": "faq_charge_scan_001",
                "chunkId": "faq_charge_scan_001#main",
                "title": "怎么扫码充电？",
                "businessDomain": "charging",
                "knowledgeType": "faq",
                "summary": "用户连接充电枪后，可以通过小程序扫码启动充电。",
                "content": "正文",
                "allowedClaims": ["允许表达"],
                "forbiddenClaims": ["禁止表达"],
                "source": {"docId": "doc_charging_faq_v1", "docTitle": "充电常见问题"},
                "knowledgeVersion": "kb_test",
            }
        )
    ])

    response = service.query(request())

    assert response.status == "success"
    assert response.answerable is True
    assert response.confidence == 0.93
    assert response.queryRewrite == "怎么扫码充电？"
    assert response.knowledgeVersion == "kb_test"
    assert response.items[0].knowledgeId == "faq_charge_scan_001"
    assert service.store.seen_channel == "wechat_mini_program"
    assert len(service.repository.audit_logs) == 1
    audit_log = service.repository.audit_logs[0]
    assert audit_log.status == "success"
    assert audit_log.query_masked == "怎么扫码充电？"
    assert audit_log.session_id_hash is not None
    assert audit_log.top_knowledge_ids == ["faq_charge_scan_001"]
    assert service.repository.gap_events == []


def test_query_not_found_when_no_points() -> None:
    service = service_with([])

    response = service.query(request())

    assert response.status == "not_found"
    assert response.answerable is False
    assert response.items == []
    assert response.fallback is not None
    assert response.fallback.reason == "no_relevant_knowledge"
    assert len(service.repository.audit_logs) == 1
    assert service.repository.audit_logs[0].status == "not_found"
    assert len(service.repository.gap_events) == 1
    gap_event = service.repository.gap_events[0]
    assert gap_event.status == "not_found"
    assert gap_event.business_domain_guess == "charging"
    assert gap_event.knowledge_type_guess == "faq"


def test_query_signal_score_boosts_similar_questions() -> None:
    service = RagQueryService.__new__(RagQueryService)

    score = service._query_signal_score(
        "第一次用这个桩怎么开始？",
        {
            "title": "怎么扫码充电？",
            "keywords": ["扫码", "二维码", "启动充电", "连接充电枪"],
            "similarQuestions": [
                "怎么扫码充电？",
                "第一次用大力仔怎么开始充电？",
                "扫哪里可以启动充电？",
            ],
        },
    )

    assert score >= 0.78


def test_query_signal_score_does_not_boost_specific_order_amount_query() -> None:
    service = RagQueryService.__new__(RagQueryService)

    score = service._query_signal_score(
        "我这笔订单为什么扣了20块？",
        {
            "title": "觉得订单扣费异常怎么办？",
            "keywords": ["扣费异常", "费用明细", "订单金额", "多扣费"],
            "similarQuestions": [
                "为什么这单扣这么多？",
                "我是不是被多扣了？",
                "这笔订单费用不对怎么办？",
            ],
        },
    )

    assert score == 0.0

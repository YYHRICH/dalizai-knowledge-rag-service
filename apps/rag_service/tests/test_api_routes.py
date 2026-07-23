from fastapi.testclient import TestClient

from apps.rag_service.app.main import create_app


def test_health() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_v1_health_ready_checks_ingest_and_qdrant(monkeypatch, tmp_path) -> None:
    from apps.rag_service.app.api import routes
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
    from apps.rag_service.app.storage.repository import IngestRunRecord, utc_now_iso

    class FakeQdrantStore:
        def __init__(self, settings):
            self.settings = settings

        def count_points(self, collection_name):
            assert collection_name == "dalizai_knowledge_v1"
            return 24

    db_url = f"sqlite:///{tmp_path / 'rag_service.db'}"
    monkeypatch.setattr(routes.settings, "rag_metadata_db_url", db_url)
    monkeypatch.setattr(routes, "QdrantKnowledgeStore", FakeQdrantStore)
    repository = MetadataRepository(SqliteDatabase(db_url))
    repository.initialize()
    repository.create_ingest_run(
        IngestRunRecord(
            ingest_id="ingest_ready",
            knowledge_version="kb_ready",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            status="success",
            total_docs=12,
            total_knowledge_items=24,
            active_items=24,
        )
    )
    client = TestClient(create_app())

    response = client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["service"] == "dalizai-rag-service"
    assert body["version"]
    assert body["qdrant"] == {"status": "ok", "pointCount": 24}


def test_query_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/rag/query",
        json={
            "requestId": "request_001",
            "traceId": "trace_001",
            "sessionId": "session_001",
            "channel": "wechat_mini_program",
            "query": "怎么扫码充电？",
        },
    )

    assert response.status_code == 401



def test_list_knowledge_gaps(monkeypatch, tmp_path) -> None:
    from apps.rag_service.app.api import routes
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
    from apps.rag_service.app.storage.repository import KnowledgeGapClusterRecord, utc_now_iso

    db_url = f"sqlite:///{tmp_path / 'rag_service.db'}"
    monkeypatch.setattr(routes.settings, "rag_metadata_db_url", db_url)
    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    repository = MetadataRepository(SqliteDatabase(db_url))
    repository.initialize()
    now = utc_now_iso()
    repository.create_gap_cluster(
        KnowledgeGapClusterRecord(
            cluster_id="gap_cluster_001",
            representative_query="二维码扫不出来怎么办？",
            cluster_title="扫码异常",
            summary="用户反馈扫码失败。",
            business_domain_guess="device",
            knowledge_type_guess="troubleshooting",
            event_count=2,
            status_breakdown={"not_found": 2},
            query_examples=["二维码扫不出来怎么办？", "扫码一直失败怎么办？"],
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    client = TestClient(create_app())

    response = client.get(
        "/v1/admin/knowledge-gaps",
        headers={"Authorization": "Bearer admin_key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["clusters"][0]["clusterId"] == "gap_cluster_001"
    assert body["clusters"][0]["clusterTitle"] == "扫码异常"
    assert body["clusters"][0]["statusBreakdown"] == {"not_found": 2}


def test_update_knowledge_gap_status(monkeypatch, tmp_path) -> None:
    from apps.rag_service.app.api import routes
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
    from apps.rag_service.app.storage.repository import KnowledgeGapClusterRecord, utc_now_iso

    db_url = f"sqlite:///{tmp_path / 'rag_service.db'}"
    monkeypatch.setattr(routes.settings, "rag_metadata_db_url", db_url)
    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    repository = MetadataRepository(SqliteDatabase(db_url))
    repository.initialize()
    now = utc_now_iso()
    repository.create_gap_cluster(
        KnowledgeGapClusterRecord(
            cluster_id="gap_cluster_001",
            representative_query="二维码扫不出来怎么办？",
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    client = TestClient(create_app())

    response = client.patch(
        "/v1/admin/knowledge-gaps/gap_cluster_001/status",
        headers={"Authorization": "Bearer admin_key"},
        json={"handledStatus": "planned", "handledBy": "ops_user", "note": "准备补知识"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["actionId"].startswith("gap_action_")
    assert body["clusterId"] == "gap_cluster_001"
    assert body["handledStatus"] == "planned"
    assert repository.get_gap_cluster("gap_cluster_001")["handled_status"] == "planned"


def test_update_knowledge_gap_status_404(monkeypatch, tmp_path) -> None:
    from apps.rag_service.app.api import routes
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase

    db_url = f"sqlite:///{tmp_path / 'rag_service.db'}"
    monkeypatch.setattr(routes.settings, "rag_metadata_db_url", db_url)
    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    MetadataRepository(SqliteDatabase(db_url)).initialize()
    client = TestClient(create_app())

    response = client.patch(
        "/v1/admin/knowledge-gaps/missing/status",
        headers={"Authorization": "Bearer admin_key"},
        json={"handledStatus": "ignored"},
    )

    assert response.status_code == 404


def test_admin_knowledge_gaps_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/admin/knowledge-gaps")

    assert response.status_code == 401



def test_ready_checks_ingest_and_qdrant(monkeypatch, tmp_path) -> None:
    from apps.rag_service.app.api import routes
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
    from apps.rag_service.app.storage.repository import IngestRunRecord, utc_now_iso

    class FakeQdrantStore:
        def __init__(self, settings):
            self.settings = settings

        def count_points(self, collection_name):
            assert collection_name == "dalizai_knowledge_v1"
            return 24

    db_url = f"sqlite:///{tmp_path / 'rag_service.db'}"
    monkeypatch.setattr(routes.settings, "rag_metadata_db_url", db_url)
    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    monkeypatch.setattr(routes, "QdrantKnowledgeStore", FakeQdrantStore)
    repository = MetadataRepository(SqliteDatabase(db_url))
    repository.initialize()
    repository.create_ingest_run(
        IngestRunRecord(
            ingest_id="ingest_ready",
            knowledge_version="kb_ready",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            status="success",
            total_docs=12,
            total_knowledge_items=24,
            active_items=24,
        )
    )
    client = TestClient(create_app())

    response = client.get("/ready", headers={"Authorization": "Bearer admin_key"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["qdrant"] == {"status": "ok", "pointCount": 24}
    assert body["latestIngest"]["ingest_id"] == "ingest_ready"



def test_debug_page() -> None:
    client = TestClient(create_app())

    response = client.get("/debug")

    assert response.status_code == 200
    assert "RAG Debug Console" in response.text


def test_list_eval_cases_endpoint(monkeypatch) -> None:
    from apps.rag_service.app.api import routes

    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    client = TestClient(create_app())

    response = client.get(
        "/v1/admin/eval-cases?source=agent",
        headers={"Authorization": "Bearer admin_key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "agent"
    assert body["count"] == 9
    assert all(item["shouldCallRag"] for item in body["cases"])


def test_list_eval_cases_can_include_not_called(monkeypatch) -> None:
    from apps.rag_service.app.api import routes

    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    client = TestClient(create_app())

    response = client.get(
        "/v1/admin/eval-cases?source=agent&includeNotCalled=true",
        headers={"Authorization": "Bearer admin_key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 12
    assert any(item["expectedStatus"] == "not_called" for item in body["cases"])


def test_debug_query_returns_response_and_evaluation(monkeypatch) -> None:
    from apps.rag_service.app.api import routes
    from apps.rag_service.app.schemas.rag import KnowledgeItemResponse, KnowledgeSource, RagQueryResponse

    class FakeRagQueryService:
        def __init__(self, settings):
            self.settings = settings

        def query(self, request):
            assert request.query == "怎么扫码充电？"
            assert request.context == {"pageContext": {"page": "order_checkout"}}
            return RagQueryResponse(
                requestId=request.requestId,
                traceId=request.traceId,
                status="success",
                answerable=True,
                confidence=0.9,
                items=[
                    KnowledgeItemResponse(
                        knowledgeId="faq_charge_scan_001",
                        chunkId="faq_charge_scan_001#main",
                        title="怎么扫码充电？",
                        summary="用户连接充电枪后，可以通过小程序扫码启动充电。",
                        content="余额不足或设备不可用时，系统会在启动前提示。",
                        score=0.9,
                        allowedClaims=["用户连接充电枪后，可以在小程序中扫码启动充电。"],
                        forbiddenClaims=[],
                        source=KnowledgeSource(docId="doc_charging_faq_v1"),
                    )
                ],
                latencyMs=12,
            )

    monkeypatch.setattr(routes.settings, "rag_admin_api_key", "admin_key")
    monkeypatch.setattr(routes, "RagQueryService", FakeRagQueryService)
    client = TestClient(create_app())

    response = client.post(
        "/v1/admin/debug/query",
        headers={"Authorization": "Bearer admin_key"},
        json={
            "requestId": "debug_test_001",
            "traceId": "trace_debug_test_001",
            "query": "怎么扫码充电？",
            "filters": {"businessDomains": ["charging"], "knowledgeTypes": ["faq"]},
            "context": {"pageContext": {"page": "order_checkout"}},
            "expectedStatus": "success",
            "expectedKnowledgeId": "faq_charge_scan_001",
            "expectedContextIds": ["faq_charge_scan_001#main"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"]["status"] == "success"
    assert body["response"]["items"][0]["knowledgeId"] == "faq_charge_scan_001"
    assert body["evaluation"]["passed"] is True
    assert body["evaluation"]["retrievedContextIds"] == ["faq_charge_scan_001#main"]

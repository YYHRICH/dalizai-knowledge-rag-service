from fastapi.testclient import TestClient

from apps.rag_service.app.main import create_app


def test_health() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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

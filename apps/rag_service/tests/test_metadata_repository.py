import sqlite3

from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
from apps.rag_service.app.storage.repository import (
    AuditLogRecord,
    IngestRunRecord,
    KnowledgeGapClusterRecord,
    KnowledgeGapEventRecord,
    new_id,
    utc_now_iso,
)


def repository_for(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'rag_service.db'}"
    repository = MetadataRepository(SqliteDatabase(db_url))
    repository.initialize()
    return repository, tmp_path / "rag_service.db"


def test_initialize_creates_expected_tables(tmp_path) -> None:
    _, db_path = repository_for(tmp_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert "ingest_runs" in table_names
    assert "audit_logs" in table_names
    assert "knowledge_gap_events" in table_names
    assert "knowledge_gap_clusters" in table_names
    assert "knowledge_gap_cluster_actions" in table_names


def test_create_and_read_latest_successful_ingest_run(tmp_path) -> None:
    repository, _ = repository_for(tmp_path)
    started_at = utc_now_iso()

    repository.create_ingest_run(
        IngestRunRecord(
            ingest_id="ingest_failed",
            knowledge_version="kb_failed",
            started_at="2026-07-23T09:00:00+00:00",
            finished_at="2026-07-23T09:01:00+00:00",
            status="failed",
            error_message="validation failed",
        )
    )
    repository.create_ingest_run(
        IngestRunRecord(
            ingest_id="ingest_success",
            knowledge_version="kb_2026_07_23_1000",
            started_at=started_at,
            finished_at=utc_now_iso(),
            status="success",
            total_docs=12,
            total_knowledge_items=24,
            active_items=24,
            qdrant_collection="dalizai_knowledge_20260723_1000",
            qdrant_alias="dalizai_knowledge_v1",
        )
    )

    latest = repository.get_latest_successful_ingest_run()

    assert latest is not None
    assert latest["ingest_id"] == "ingest_success"
    assert latest["knowledge_version"] == "kb_2026_07_23_1000"
    assert latest["total_docs"] == 12


def test_create_audit_log(tmp_path) -> None:
    repository, db_path = repository_for(tmp_path)

    repository.create_audit_log(
        AuditLogRecord(
            audit_id=new_id("audit"),
            request_id="request_001",
            trace_id="trace_001",
            session_id_hash="session_hash",
            user_id_hash="user_hash",
            channel="wechat_mini_program",
            original_query_masked="怎么扫码充电？",
            query_masked="扫码充电操作步骤",
            intent="faq",
            sub_intent="charge_scan_guide",
            filters={"businessDomains": ["charging"]},
            status="success",
            answerable=True,
            confidence=0.91,
            top_knowledge_ids=["faq_charge_scan_001"],
            top_chunk_ids=["faq_charge_scan_001#main"],
            top_doc_ids=["doc_charging_faq_v1"],
            knowledge_version="kb_2026_07_23_1000",
            latency_ms=128,
        )
    )

    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT * FROM audit_logs").fetchone()

    assert row is not None
    assert row[1] == "request_001"
    assert row[11] == "success"
    assert row[12] == 1


def test_gap_cluster_event_and_status_update(tmp_path) -> None:
    repository, _ = repository_for(tmp_path)
    now = utc_now_iso()
    cluster_id = "gap_cluster_001"

    repository.create_gap_cluster(
        KnowledgeGapClusterRecord(
            cluster_id=cluster_id,
            representative_query="二维码扫不出来怎么办？",
            cluster_title="二维码无法识别",
            summary="用户反馈扫码失败或二维码无法识别。",
            business_domain_guess="device",
            knowledge_type_guess="troubleshooting",
            owner_team="设备运营",
            event_count=1,
            status_breakdown={"not_found": 1},
            query_examples=["二维码扫不出来怎么办？"],
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    repository.create_gap_event(
        KnowledgeGapEventRecord(
            gap_event_id="gap_event_001",
            cluster_id=cluster_id,
            request_id="request_gap_001",
            trace_id="trace_gap_001",
            channel="wechat_mini_program",
            query_masked="二维码扫不出来怎么办？",
            status="not_found",
            confidence=0.0,
            business_domain_guess="device",
            knowledge_type_guess="troubleshooting",
        )
    )
    action_id = repository.update_gap_cluster_status(
        cluster_id,
        "resolved",
        handled_by="ops_user_001",
        note="已补充故障排查知识。",
    )

    clusters = repository.list_gap_clusters("resolved")

    assert action_id.startswith("gap_action_")
    assert len(clusters) == 1
    assert clusters[0]["cluster_id"] == cluster_id
    assert clusters[0]["handled_status"] == "resolved"


def test_list_and_assign_unclustered_gap_events(tmp_path) -> None:
    repository, db_path = repository_for(tmp_path)
    repository.create_gap_event(
        KnowledgeGapEventRecord(
            gap_event_id="gap_event_unclustered",
            request_id="request_gap_unclustered",
            trace_id="trace_gap_unclustered",
            channel="wechat_mini_program",
            query_masked="二维码扫不出来怎么办？",
            status="not_found",
            filters={"businessDomains": ["device"]},
            business_domain_guess="device",
            top_candidate_knowledge_ids=["candidate_001"],
        )
    )

    events = repository.list_unclustered_gap_events(limit=10)

    assert len(events) == 1
    assert events[0]["gap_event_id"] == "gap_event_unclustered"
    assert events[0]["filters"] == {"businessDomains": ["device"]}
    assert events[0]["top_candidate_knowledge_ids"] == ["candidate_001"]

    now = utc_now_iso()
    repository.create_gap_cluster(
        KnowledgeGapClusterRecord(
            cluster_id="gap_cluster_001",
            representative_query="二维码扫不出来怎么办？",
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    repository.assign_gap_events_to_cluster(["gap_event_unclustered"], "gap_cluster_001")

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT cluster_id FROM knowledge_gap_events WHERE gap_event_id = ?",
            ("gap_event_unclustered",),
        ).fetchone()
    assert row[0] == "gap_cluster_001"

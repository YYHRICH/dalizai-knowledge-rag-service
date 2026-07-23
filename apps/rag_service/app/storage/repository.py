from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .database import SqliteDatabase


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class IngestRunRecord:
    ingest_id: str
    knowledge_version: str
    started_at: str
    status: str
    total_docs: int = 0
    total_knowledge_items: int = 0
    active_items: int = 0
    skipped_items: int = 0
    failed_items: int = 0
    finished_at: str | None = None
    qdrant_collection: str | None = None
    qdrant_alias: str | None = None
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditLogRecord:
    audit_id: str
    request_id: str
    trace_id: str
    channel: str
    query_masked: str
    status: str
    answerable: bool = False
    confidence: float = 0.0
    session_id_hash: str | None = None
    user_id_hash: str | None = None
    original_query_masked: str | None = None
    intent: str | None = None
    sub_intent: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    top_knowledge_ids: list[str] = field(default_factory=list)
    top_chunk_ids: list[str] = field(default_factory=list)
    top_doc_ids: list[str] = field(default_factory=list)
    knowledge_version: str | None = None
    latency_ms: int | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class KnowledgeGapClusterRecord:
    cluster_id: str
    representative_query: str
    first_seen_at: str
    last_seen_at: str
    cluster_title: str | None = None
    summary: str | None = None
    business_domain_guess: str | None = None
    knowledge_type_guess: str | None = None
    owner_team: str | None = None
    event_count: int = 0
    status_breakdown: dict[str, int] = field(default_factory=dict)
    top_candidate_knowledge_ids: list[str] = field(default_factory=list)
    query_examples: list[str] = field(default_factory=list)
    handled_status: str = "open"


@dataclass(frozen=True)
class KnowledgeGapEventRecord:
    gap_event_id: str
    request_id: str
    trace_id: str
    channel: str
    query_masked: str
    status: str
    confidence: float = 0.0
    cluster_id: str | None = None
    session_id_hash: str | None = None
    user_id_hash: str | None = None
    original_query_masked: str | None = None
    intent: str | None = None
    sub_intent: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    business_domain_guess: str | None = None
    knowledge_type_guess: str | None = None
    top_candidate_knowledge_ids: list[str] = field(default_factory=list)


class MetadataRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def initialize(self) -> None:
        self.database.initialize()

    def create_ingest_run(self, record: IngestRunRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO ingest_runs (
                    ingest_id, knowledge_version, started_at, finished_at, status,
                    total_docs, total_knowledge_items, active_items, skipped_items,
                    failed_items, qdrant_collection, qdrant_alias, error_message,
                    warnings_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.ingest_id,
                    record.knowledge_version,
                    record.started_at,
                    record.finished_at,
                    record.status,
                    record.total_docs,
                    record.total_knowledge_items,
                    record.active_items,
                    record.skipped_items,
                    record.failed_items,
                    record.qdrant_collection,
                    record.qdrant_alias,
                    record.error_message,
                    json.dumps(record.warnings, ensure_ascii=False),
                ),
            )

    def get_latest_successful_ingest_run(self) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM ingest_runs
                WHERE status IN ('success', 'success_with_warnings')
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
            return dict(row) if row else None

    def create_audit_log(self, record: AuditLogRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_logs (
                    audit_id, request_id, trace_id, session_id_hash, user_id_hash,
                    channel, original_query_masked, query_masked, intent, sub_intent,
                    filters_json, status, answerable, confidence,
                    top_knowledge_ids_json, top_chunk_ids_json, top_doc_ids_json,
                    knowledge_version, latency_ms, error_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.audit_id,
                    record.request_id,
                    record.trace_id,
                    record.session_id_hash,
                    record.user_id_hash,
                    record.channel,
                    record.original_query_masked,
                    record.query_masked,
                    record.intent,
                    record.sub_intent,
                    json.dumps(record.filters, ensure_ascii=False),
                    record.status,
                    int(record.answerable),
                    record.confidence,
                    json.dumps(record.top_knowledge_ids, ensure_ascii=False),
                    json.dumps(record.top_chunk_ids, ensure_ascii=False),
                    json.dumps(record.top_doc_ids, ensure_ascii=False),
                    record.knowledge_version,
                    record.latency_ms,
                    record.error_code,
                ),
            )

    def create_gap_cluster(self, record: KnowledgeGapClusterRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_gap_clusters (
                    cluster_id, representative_query, cluster_title, summary,
                    business_domain_guess, knowledge_type_guess, owner_team,
                    event_count, status_breakdown_json,
                    top_candidate_knowledge_ids_json, query_examples_json,
                    handled_status, first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.cluster_id,
                    record.representative_query,
                    record.cluster_title,
                    record.summary,
                    record.business_domain_guess,
                    record.knowledge_type_guess,
                    record.owner_team,
                    record.event_count,
                    json.dumps(record.status_breakdown, ensure_ascii=False),
                    json.dumps(record.top_candidate_knowledge_ids, ensure_ascii=False),
                    json.dumps(record.query_examples, ensure_ascii=False),
                    record.handled_status,
                    record.first_seen_at,
                    record.last_seen_at,
                ),
            )

    def create_gap_event(self, record: KnowledgeGapEventRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_gap_events (
                    gap_event_id, cluster_id, request_id, trace_id, session_id_hash,
                    user_id_hash, channel, original_query_masked, query_masked,
                    intent, sub_intent, filters_json, status, confidence,
                    business_domain_guess, knowledge_type_guess,
                    top_candidate_knowledge_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.gap_event_id,
                    record.cluster_id,
                    record.request_id,
                    record.trace_id,
                    record.session_id_hash,
                    record.user_id_hash,
                    record.channel,
                    record.original_query_masked,
                    record.query_masked,
                    record.intent,
                    record.sub_intent,
                    json.dumps(record.filters, ensure_ascii=False),
                    record.status,
                    record.confidence,
                    record.business_domain_guess,
                    record.knowledge_type_guess,
                    json.dumps(record.top_candidate_knowledge_ids, ensure_ascii=False),
                ),
            )

    def update_gap_cluster_status(
        self,
        cluster_id: str,
        handled_status: str,
        handled_by: str | None = None,
        note: str | None = None,
    ) -> str:
        action_id = new_id("gap_action")
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE knowledge_gap_clusters
                SET handled_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
                """,
                (handled_status, cluster_id),
            )
            connection.execute(
                """
                INSERT INTO knowledge_gap_cluster_actions (
                    action_id, cluster_id, handled_status, handled_by, note
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (action_id, cluster_id, handled_status, handled_by, note),
            )
        return action_id

    def list_gap_clusters(self, handled_status: str | None = None) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            if handled_status:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_gap_clusters
                    WHERE handled_status = ?
                    ORDER BY last_seen_at DESC
                    """,
                    (handled_status,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_gap_clusters
                    ORDER BY last_seen_at DESC
                    """
                ).fetchall()
            return [dict(row) for row in rows]

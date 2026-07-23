from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteDatabase:
    def __init__(self, db_url: str = "sqlite:///data/rag_service.db") -> None:
        self.db_path = self._parse_sqlite_url(db_url)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def _parse_sqlite_url(self, db_url: str) -> Path:
        prefix = "sqlite:///"
        if not db_url.startswith(prefix):
            raise ValueError("Only sqlite:/// URLs are supported in v1")
        raw_path = db_url[len(prefix) :]
        if not raw_path:
            raise ValueError("SQLite path cannot be empty")
        return Path(raw_path)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ingest_runs (
    ingest_id TEXT PRIMARY KEY,
    knowledge_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    total_docs INTEGER NOT NULL DEFAULT 0,
    total_knowledge_items INTEGER NOT NULL DEFAULT 0,
    active_items INTEGER NOT NULL DEFAULT 0,
    skipped_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    qdrant_collection TEXT,
    qdrant_alias TEXT,
    error_message TEXT,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ingest_runs_started_at ON ingest_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_status ON ingest_runs(status);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    session_id_hash TEXT,
    user_id_hash TEXT,
    channel TEXT NOT NULL,
    original_query_masked TEXT,
    query_masked TEXT NOT NULL,
    intent TEXT,
    sub_intent TEXT,
    filters_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    answerable INTEGER NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0,
    top_knowledge_ids_json TEXT NOT NULL DEFAULT '[]',
    top_chunk_ids_json TEXT NOT NULL DEFAULT '[]',
    top_doc_ids_json TEXT NOT NULL DEFAULT '[]',
    knowledge_version TEXT,
    latency_ms INTEGER,
    error_code TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_trace_id ON audit_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_status ON audit_logs(status);

CREATE TABLE IF NOT EXISTS knowledge_gap_clusters (
    cluster_id TEXT PRIMARY KEY,
    representative_query TEXT NOT NULL,
    cluster_title TEXT,
    summary TEXT,
    business_domain_guess TEXT,
    knowledge_type_guess TEXT,
    owner_team TEXT,
    event_count INTEGER NOT NULL DEFAULT 0,
    status_breakdown_json TEXT NOT NULL DEFAULT '{}',
    top_candidate_knowledge_ids_json TEXT NOT NULL DEFAULT '[]',
    query_examples_json TEXT NOT NULL DEFAULT '[]',
    handled_status TEXT NOT NULL DEFAULT 'open',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gap_clusters_handled_status
ON knowledge_gap_clusters(handled_status);
CREATE INDEX IF NOT EXISTS idx_gap_clusters_last_seen_at
ON knowledge_gap_clusters(last_seen_at);

CREATE TABLE IF NOT EXISTS knowledge_gap_events (
    gap_event_id TEXT PRIMARY KEY,
    cluster_id TEXT,
    request_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    session_id_hash TEXT,
    user_id_hash TEXT,
    channel TEXT NOT NULL,
    original_query_masked TEXT,
    query_masked TEXT NOT NULL,
    intent TEXT,
    sub_intent TEXT,
    filters_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    business_domain_guess TEXT,
    knowledge_type_guess TEXT,
    top_candidate_knowledge_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cluster_id) REFERENCES knowledge_gap_clusters(cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_gap_events_cluster_id ON knowledge_gap_events(cluster_id);
CREATE INDEX IF NOT EXISTS idx_gap_events_created_at ON knowledge_gap_events(created_at);
CREATE INDEX IF NOT EXISTS idx_gap_events_status ON knowledge_gap_events(status);

CREATE TABLE IF NOT EXISTS knowledge_gap_cluster_actions (
    action_id TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    handled_status TEXT NOT NULL,
    handled_by TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cluster_id) REFERENCES knowledge_gap_clusters(cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_gap_actions_cluster_id
ON knowledge_gap_cluster_actions(cluster_id);
"""

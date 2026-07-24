"""SQLite 数据库连接管理。

封装 SQLite 连接和初始化逻辑。第一版仅支持 ``sqlite:///`` 前缀的本地文件数据库，
使用 WAL 日志模式提高并发读取性能。所有表通过 ``CREATE TABLE IF NOT EXISTS`` 保证幂等初始化。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteDatabase:
    """SQLite 数据库连接管理器。

    负责：
    - 解析 ``sqlite:///path`` 格式的数据库 URL
    - 创建数据库文件所在目录（如不存在）
    - 开启 WAL 日志模式和外键约束
    - 初始化所有元数据表结构
    """

    def __init__(self, db_url: str = "sqlite:///data/rag_service.db") -> None:
        """初始化连接管理器，解析数据库文件路径。

        Args:
            db_url: SQLite 数据库 URL，格式 ``sqlite:///relative/or/absolute/path``。
        """
        self.db_path = self._parse_sqlite_url(db_url)

    def connect(self) -> sqlite3.Connection:
        """创建并返回一个新的数据库连接。

        每次调用都会创建新连接，使用 sqlite3.Row 作为行工厂以支持字典式访问。
        自动创建数据库文件所在目录。

        Returns:
            已配置好 pragma 和行工厂的 sqlite3.Connection。
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        """执行建表 SQL，初始化所有元数据表。幂等操作，重复执行安全。"""
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def _parse_sqlite_url(self, db_url: str) -> Path:
        """解析 ``sqlite:///`` 格式的 URL 为文件系统路径。

        Args:
            db_url: 数据库 URL。

        Returns:
            数据库文件的 Path 对象。

        Raises:
            ValueError: URL 格式不正确或路径为空。
        """
        prefix = "sqlite:///"
        if not db_url.startswith(prefix):
            raise ValueError("Only sqlite:/// URLs are supported in v1")
        raw_path = db_url[len(prefix) :]
        if not raw_path:
            raise ValueError("SQLite path cannot be empty")
        return Path(raw_path)


# ═══════════════════════════════════════════════════════════════
# 数据库 Schema
# ═══════════════════════════════════════════════════════════════
#
# 5 张表的设计分工：
#
# 1. ingest_runs — 知识入库运行记录，记录每次 ingest 的版本、数量、状态。
# 2. audit_logs — RAG 查询审计日志，所有 PII 已脱敏/hash。
# 3. knowledge_gap_clusters — 知识缺口集群，由聚类服务自动生成。
# 4. knowledge_gap_events — 知识缺口事件，每次 not_found / low_confidence 时记录。
# 5. knowledge_gap_cluster_actions — 缺口集群处理操作审计记录。
# ═══════════════════════════════════════════════════════════════

SCHEMA_SQL = """
-- ── 入库运行记录 ────────────────────────────────────────────
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

-- ── RAG 查询审计日志 ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    session_id_hash TEXT,          -- SHA-256 hash(salt + sessionId)，不存明文
    user_id_hash TEXT,             -- SHA-256 hash(salt + userId)，不存明文
    channel TEXT NOT NULL,
    original_query_masked TEXT,    -- PII 脱敏后的原始查询
    query_masked TEXT NOT NULL,    -- PII 脱敏后的查询文本
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

-- ── 知识缺口集群 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_gap_clusters (
    cluster_id TEXT PRIMARY KEY,
    representative_query TEXT NOT NULL,
    cluster_title TEXT,            -- LLM 生成的标题（≤20 字）
    summary TEXT,                  -- LLM 生成的摘要（≤80 字）
    business_domain_guess TEXT,
    knowledge_type_guess TEXT,
    owner_team TEXT,
    event_count INTEGER NOT NULL DEFAULT 0,
    status_breakdown_json TEXT NOT NULL DEFAULT '{}',         -- {"not_found": N, "low_confidence": N}
    top_candidate_knowledge_ids_json TEXT NOT NULL DEFAULT '[]',
    query_examples_json TEXT NOT NULL DEFAULT '[]',
    handled_status TEXT NOT NULL DEFAULT 'open',              -- open / planned / resolved / ignored
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gap_clusters_handled_status
ON knowledge_gap_clusters(handled_status);
CREATE INDEX IF NOT EXISTS idx_gap_clusters_last_seen_at
ON knowledge_gap_clusters(last_seen_at);

-- ── 知识缺口事件 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_gap_events (
    gap_event_id TEXT PRIMARY KEY,
    cluster_id TEXT,               -- 所属集群 ID，未聚类时为 NULL
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
    status TEXT NOT NULL,          -- not_found 或 low_confidence
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

-- ── 缺口集群处理操作记录 ────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_gap_cluster_actions (
    action_id TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    handled_status TEXT NOT NULL,  -- 操作后的状态
    handled_by TEXT,               -- 处理人
    note TEXT,                     -- 处理备注
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cluster_id) REFERENCES knowledge_gap_clusters(cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_gap_actions_cluster_id
ON knowledge_gap_cluster_actions(cluster_id);
"""

"""SQLite 元数据仓储层。

封装所有对 SQLite 元数据库的读写操作，包括：
- 入库运行记录（ingest_runs）
- 审计日志（audit_logs）
- 知识缺口事件和集群（knowledge_gap_events / knowledge_gap_clusters）

所有数据模型使用 frozen dataclass 保证不可变性。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .database import SqliteDatabase


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。用于入库记录和审计日志的时间戳。"""
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    """生成带前缀的唯一 ID。

    格式为 ``{prefix}_{uuid4_hex}``，用于 audit_id、gap_event_id、cluster_id 等。
    """
    return f"{prefix}_{uuid.uuid4().hex}"


# ═══════════════════════════════════════════════════════════════
# 数据记录类型（frozen dataclass，不可变）
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class IngestRunRecord:
    """一次知识入库运行的记录。

    每次执行 ``scripts/ingest_knowledge.py`` 会创建一条记录。
    """

    ingest_id: str
    """入库运行唯一 ID。"""

    knowledge_version: str
    """本次入库生成的知识版本号。"""

    started_at: str
    """入库开始时间（ISO 8601）。"""

    status: str
    """入库状态：success / success_with_warnings / failed。"""

    total_docs: int = 0
    """处理的 Markdown 文档总数。"""

    total_knowledge_items: int = 0
    """所有文档中的知识条目总数。"""

    active_items: int = 0
    """成功入库的条目数。"""

    skipped_items: int = 0
    """跳过的条目数。"""

    failed_items: int = 0
    """入库失败的条目数。"""

    finished_at: str | None = None
    """入库完成时间。"""

    qdrant_collection: str | None = None
    """本次入库创建的 Qdrant collection 名称。"""

    qdrant_alias: str | None = None
    """关联的 Qdrant alias 名称。"""

    error_message: str | None = None
    """失败时的错误信息。"""

    warnings: list[str] = field(default_factory=list)
    """入库过程中的 warning 消息列表。"""


@dataclass(frozen=True)
class AuditLogRecord:
    """一条 RAG 查询的审计日志。

    每次 POST /v1/rag/query 调用都会创建一条审计记录。
    PII 字段（sessionId、userId、query）已经过脱敏/hash 处理。
    """

    audit_id: str
    """审计日志唯一 ID。"""

    request_id: str
    """原请求的 requestId。"""

    trace_id: str
    """原请求的 traceId。"""

    channel: str
    """来源渠道。"""

    query_masked: str
    """脱敏后的查询文本。"""

    status: str
    """RAG 返回状态。"""

    answerable: bool = False
    """是否可回答。"""

    confidence: float = 0.0
    """检索置信度。"""

    session_id_hash: str | None = None
    """SHA-256 哈希后的会话 ID。"""

    user_id_hash: str | None = None
    """SHA-256 哈希后的用户 ID。"""

    original_query_masked: str | None = None
    """脱敏后的原始查询文本。"""

    intent: str | None = None
    """Agent 识别的主意图。"""

    sub_intent: str | None = None
    """Agent 识别的子意图。"""

    filters: dict[str, Any] = field(default_factory=dict)
    """检索过滤条件。"""

    top_knowledge_ids: list[str] = field(default_factory=list)
    """返回的排名前 K 知识 ID 列表。"""

    top_chunk_ids: list[str] = field(default_factory=list)
    """返回的排名前 K chunk ID 列表。"""

    top_doc_ids: list[str] = field(default_factory=list)
    """返回的排名前 K 文档 ID 列表。"""

    knowledge_version: str | None = None
    """知识库版本号。"""

    latency_ms: int | None = None
    """请求耗时（毫秒）。"""

    error_code: str | None = None
    """错误码（如有）。"""


@dataclass(frozen=True)
class KnowledgeGapClusterRecord:
    """一个知识缺口集群。

    由 GapClusteringService 对相似的缺口事件聚类生成。
    """

    cluster_id: str
    """集群唯一 ID。"""

    representative_query: str
    """代表性查询文本。"""

    first_seen_at: str
    """首次出现时间。"""

    last_seen_at: str
    """最近出现时间。"""

    cluster_title: str | None = None
    """LLM 生成的集群标题。"""

    summary: str | None = None
    """LLM 生成的集群摘要。"""

    business_domain_guess: str | None = None
    """推测的业务域。"""

    knowledge_type_guess: str | None = None
    """推测的知识类型。"""

    owner_team: str | None = None
    """应负责处理的团队。"""

    event_count: int = 0
    """集群包含的事件数。"""

    status_breakdown: dict[str, int] = field(default_factory=dict)
    """事件状态分布。"""

    top_candidate_knowledge_ids: list[str] = field(default_factory=list)
    """高频候选知识 ID。"""

    query_examples: list[str] = field(default_factory=list)
    """查询示例。"""

    handled_status: str = "open"
    """处理状态：open / planned / resolved / ignored。"""


@dataclass(frozen=True)
class KnowledgeGapEventRecord:
    """一条知识缺口事件。

    当 RAG 返回 not_found 或 low_confidence 时自动创建。
    用于后续聚类分析，发现知识盲区。
    """

    gap_event_id: str
    """缺口事件唯一 ID。"""

    request_id: str
    """原请求 ID。"""

    trace_id: str
    """原链路追踪 ID。"""

    channel: str
    """来源渠道。"""

    query_masked: str
    """脱敏后的查询文本。"""

    status: str
    """RAG 状态（not_found 或 low_confidence）。"""

    confidence: float = 0.0
    """检索置信度。"""

    cluster_id: str | None = None
    """所属集群 ID（未聚类时为 None）。"""

    session_id_hash: str | None = None
    """哈希后的会话 ID。"""

    user_id_hash: str | None = None
    """哈希后的用户 ID。"""

    original_query_masked: str | None = None
    """脱敏后的原始查询。"""

    intent: str | None = None
    """Agent 识别的主意图。"""

    sub_intent: str | None = None
    """Agent 识别的子意图。"""

    filters: dict[str, Any] = field(default_factory=dict)
    """检索过滤条件。"""

    business_domain_guess: str | None = None
    """从 filter 中提取的业务域。"""

    knowledge_type_guess: str | None = None
    """从 filter 中提取的知识类型。"""

    top_candidate_knowledge_ids: list[str] = field(default_factory=list)
    """查询时返回的候选知识 ID（尽管置信度不够）。"""


# ═══════════════════════════════════════════════════════════════
# 仓储类
# ═══════════════════════════════════════════════════════════════


class MetadataRepository:
    """元数据仓储。

    封装所有对 SQLite 元数据库的 CRUD 操作。
    使用时需要先调用 ``initialize()`` 确保表结构存在。
    """

    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def initialize(self) -> None:
        """初始化数据库表结构（如不存在则创建）。幂等操作。"""
        self.database.initialize()

    # ── 入库记录 ─────────────────────────────────────────────

    def create_ingest_run(self, record: IngestRunRecord) -> None:
        """创建一条入库运行记录。"""
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
        """获取最近一次成功入库的运行记录。用于就绪检查时判断知识库是否已初始化。"""
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

    # ── 审计日志 ─────────────────────────────────────────────

    def create_audit_log(self, record: AuditLogRecord) -> None:
        """创建一条 RAG 查询审计日志。

        所有 PII 字段在上层已通过 ``mask_text`` 和 ``hash_identifier`` 处理。
        """
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

    # ── 知识缺口事件 ─────────────────────────────────────────

    def list_unclustered_gap_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取尚未分配到任何集群的缺口事件。按创建时间升序，先创建的优先处理。"""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM knowledge_gap_events
                WHERE cluster_id IS NULL
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._decode_gap_event_row(dict(row)) for row in rows]

    def assign_gap_events_to_cluster(self, gap_event_ids: list[str], cluster_id: str) -> None:
        """将一批缺口事件分配到指定集群。"""
        if not gap_event_ids:
            return
        with self.database.connect() as connection:
            connection.executemany(
                """
                UPDATE knowledge_gap_events
                SET cluster_id = ?
                WHERE gap_event_id = ?
                """,
                [(cluster_id, gap_event_id) for gap_event_id in gap_event_ids],
            )

    def create_gap_event(self, record: KnowledgeGapEventRecord) -> None:
        """创建一条缺口事件记录。在 RAG 查询返回 not_found 或 low_confidence 时调用。"""
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

    # ── 知识缺口集群 ─────────────────────────────────────────

    def list_open_gap_clusters(self) -> list[dict[str, Any]]:
        """获取所有未处理（open 状态）的缺口集群。按最近出现时间降序。"""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM knowledge_gap_clusters
                WHERE handled_status = 'open'
                ORDER BY last_seen_at DESC
                """
            ).fetchall()
        return [self._decode_gap_cluster_row(dict(row)) for row in rows]

    def upsert_gap_cluster(self, record: KnowledgeGapClusterRecord) -> None:
        """插入或更新缺口集群。

        如果 cluster_id 已存在则更新（合并新事件），否则创建新集群。
        用于增量聚类：新事件可能合并到已有集群。
        """
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
                ON CONFLICT(cluster_id) DO UPDATE SET
                    representative_query = excluded.representative_query,
                    cluster_title = excluded.cluster_title,
                    summary = excluded.summary,
                    business_domain_guess = excluded.business_domain_guess,
                    knowledge_type_guess = excluded.knowledge_type_guess,
                    owner_team = excluded.owner_team,
                    event_count = excluded.event_count,
                    status_breakdown_json = excluded.status_breakdown_json,
                    top_candidate_knowledge_ids_json = excluded.top_candidate_knowledge_ids_json,
                    query_examples_json = excluded.query_examples_json,
                    first_seen_at = excluded.first_seen_at,
                    last_seen_at = excluded.last_seen_at,
                    updated_at = CURRENT_TIMESTAMP
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

    def create_gap_cluster(self, record: KnowledgeGapClusterRecord) -> None:
        """创建新的缺口集群（不检查冲突）。通常使用 ``upsert_gap_cluster`` 代替。"""
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

    def update_gap_cluster_status(
        self,
        cluster_id: str,
        handled_status: str,
        handled_by: str | None = None,
        note: str | None = None,
    ) -> str:
        """更新缺口集群的处理状态。

        同时会在 gap_cluster_actions 表中创建一条操作审计记录。
        返回本次操作的 action_id。
        """
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

    def list_gap_clusters(
        self,
        handled_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """分页查询缺口集群，可按处理状态过滤。按最近出现时间降序。"""
        with self.database.connect() as connection:
            if handled_status:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_gap_clusters
                    WHERE handled_status = ?
                    ORDER BY last_seen_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (handled_status, limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM knowledge_gap_clusters
                    ORDER BY last_seen_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            return [self._decode_gap_cluster_row(dict(row)) for row in rows]

    def get_gap_cluster(self, cluster_id: str) -> dict[str, Any] | None:
        """按 ID 获取单个缺口集群。不存在时返回 None。"""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM knowledge_gap_clusters
                WHERE cluster_id = ?
                """,
                (cluster_id,),
            ).fetchone()
        return self._decode_gap_cluster_row(dict(row)) if row else None

    # ── 内部：JSON 字段解码 ──────────────────────────────────

    def _decode_gap_event_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """将数据库行中的 JSON 字符串字段反序列化为 Python 对象。"""
        row["filters"] = json.loads(row.pop("filters_json") or "{}")
        row["top_candidate_knowledge_ids"] = json.loads(
            row.pop("top_candidate_knowledge_ids_json") or "[]"
        )
        return row

    def _decode_gap_cluster_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """将数据库行中的 JSON 字符串字段反序列化为 Python 对象。"""
        row["status_breakdown"] = json.loads(row.pop("status_breakdown_json") or "{}")
        row["top_candidate_knowledge_ids"] = json.loads(
            row.pop("top_candidate_knowledge_ids_json") or "[]"
        )
        row["query_examples"] = json.loads(row.pop("query_examples_json") or "[]")
        return row

"""RAG 查询服务 —— 系统的核心编排层。

这是整个 RAG 检索链路的总入口，负责编排以下步骤：

1. **Query Rewrite**: 调用 Chat 模型将口语查询改写为检索短句。
2. **Embedding**: 将改写后的查询向量化。
3. **向量检索**: 在 Qdrant 中通过余弦相似度召回候选。
4. **Rerank**: 调用 Rerank 模型对候选重新排序。
5. **信号增强**: 加权关键词/相似问法的文本匹配分数（与 rerank score 取 max）。
6. **阈值分档**: 按 confidence 分为 success / low_confidence / not_found。
7. **审计记录**: 每次查询写入审计日志和（如适用）知识缺口事件。

关键设计决策：
- Rerank score 和文本信号 score 取最大值而非加权平均，因为精确关键词匹配
  可能被向量语义检索遗漏，两种信号互补。
- 审计日志和缺口记录写入失败不阻塞查询响应（静默降级）。
"""

from __future__ import annotations

import time
from typing import Any

from apps.rag_service.app.core.config import Settings
from apps.rag_service.app.providers.dashscope import (
    DashScopeChatClient,
    DashScopeEmbeddingClient,
    DashScopeRerankClient,
    DashScopeSettings,
)
from apps.rag_service.app.providers.errors import ModelProviderError
from apps.rag_service.app.privacy import hash_identifier, mask_text
from apps.rag_service.app.providers.models import RerankDocument
from apps.rag_service.app.retrievers import QdrantKnowledgeStore, QdrantStoreSettings
from apps.rag_service.app.schemas.rag import (
    KnowledgeItemResponse,
    KnowledgeSource,
    RagError,
    RagFallback,
    RagQueryRequest,
    RagQueryResponse,
)
from apps.rag_service.app.services.query_rewriter import QueryRewriter
from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
from apps.rag_service.app.storage.repository import (
    AuditLogRecord,
    KnowledgeGapEventRecord,
    new_id,
)


class RagQueryService:
    """RAG 查询服务。

    对每次 POST /v1/rag/query 请求执行完整的检索链路，
    返回结构化的知识条目和置信度供 Agent 决策。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化查询服务。创建模型客户端、Qdrant 存储、元数据仓储、
        Query Rewriter 等所有依赖。每次请求构造新实例，不做单例复用。

        Args:
            settings: 全局配置。
        """
        self.settings = settings
        # 构建 DashScope 连接配置（三个 client 共享同一组认证信息）
        model_settings = DashScopeSettings(
            api_key=settings.dashscope_api_key,
            embedding_base_url=settings.dashscope_embedding_base_url,
            rerank_base_url=settings.dashscope_rerank_base_url,
            chat_base_url=settings.dashscope_chat_base_url,
            embedding_model=settings.embedding_model,
            embedding_dimension=settings.embedding_dimension,
            rerank_model=settings.rerank_model,
            chat_model=settings.query_rewrite_chat_model,
        )
        self.embedding_client = DashScopeEmbeddingClient(model_settings)
        self.rerank_client = DashScopeRerankClient(model_settings)
        self.query_rewrite_client = DashScopeChatClient(model_settings)
        self.store = QdrantKnowledgeStore(
            QdrantStoreSettings(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                collection_alias=settings.qdrant_collection_alias,
                collection_prefix=settings.qdrant_collection_prefix,
                vector_size=settings.embedding_dimension,
            )
        )
        self.repository = MetadataRepository(SqliteDatabase(settings.rag_metadata_db_url))
        self.repository.initialize()
        self.query_rewriter = QueryRewriter(self.query_rewrite_client)

    def query(self, request: RagQueryRequest) -> RagQueryResponse:
        """执行完整的 RAG 检索链路。

        流程：
        1. 确定 top_k 和 recall_limit（max(topK, rerank_top_n)）。
        2. Query Rewrite：口语 → 检索短句。
        3. Embedding + Qdrant 向量检索。
        4. 无候选 → not_found。
        5. Rerank 重排序。
        6. 文本信号增强：max(rerank_score, text_signal_score)。
        7. 阈值分档并返回。

        Args:
            request: RAG 查询请求。

        Returns:
            RagQueryResponse: 结构化检索结果，含知识条目、置信度和兜底建议。
        """
        started = time.perf_counter()
        # ── 确定 top_k 和 recall_limit ──────────────────
        top_k = min(request.topK or self.settings.rag_default_top_k, self.settings.rag_max_top_k)
        recall_limit = max(top_k, self.settings.rerank_top_n)

        # ── Query Rewrite ───────────────────────────────
        query_rewrite = self.query_rewriter.rewrite(request)

        # ── Embedding + Qdrant 向量检索 ─────────────────
        try:
            embedding = self.embedding_client.embed_texts([query_rewrite]).embeddings[0]
            points = self.store.search(
                collection_name=self.settings.qdrant_collection_alias,
                query_vector=embedding,
                filters=request.filters,
                limit=recall_limit,
                channel=request.channel,
            )
        except ModelProviderError as exc:
            return self._error_response(request, started, "rag_embedding_failed", str(exc), exc.retryable)
        except Exception as exc:
            return self._error_response(request, started, "rag_qdrant_query_failed", str(exc), True)

        # ── 无候选 → not_found ─────────────────────────
        if not points:
            return self._response(
                request,
                status="not_found",
                answerable=False,
                confidence=0.0,
                queryRewrite=query_rewrite,
                items=[],
                fallback=RagFallback(reason="no_relevant_knowledge", suggestedAction="clarify_or_handoff"),
                started=started,
            )

        # ── Rerank 重排序 ──────────────────────────────
        # 构建 rerank 输入：用 chunkId 作为 id，把知识各字段拼接为 text
        rerank_docs = [
            RerankDocument(id=str(point.payload.get("chunkId")), text=self._rerank_text(point.payload))
            for point in points
        ]
        try:
            rerank_results = self.rerank_client.rerank(query_rewrite, rerank_docs, top_n=top_k)
        except ModelProviderError as exc:
            return self._error_response(request, started, "rag_rerank_failed", str(exc), exc.retryable)

        # chunkId → point 映射，用于将 rerank 结果关联回原始 payload
        point_by_chunk_id = {str(point.payload.get("chunkId")): point for point in points}

        # ── 信号增强：max(rerank_score, text_signal_score) ──
        # 取最大值：精确关键词/相似问法匹配（文本信号）可能被向量检索遗漏
        ranked_points: list[tuple[Any, float]] = []
        for result in rerank_results:
            point = point_by_chunk_id.get(result.id)
            if point:
                score = max(result.score, self._query_signal_score(query_rewrite, point.payload))
                ranked_points.append((point, score))
        ranked_points.sort(key=lambda item: item[1], reverse=True)

        # 极端情况：rerank 结果全部无法关联到原始 point
        if not ranked_points:
            return self._response(
                request,
                status="not_found",
                answerable=False,
                confidence=0.0,
                queryRewrite=query_rewrite,
                items=[],
                fallback=RagFallback(reason="no_relevant_knowledge", suggestedAction="clarify_or_handoff"),
                started=started,
            )

        # ── 阈值分档 ───────────────────────────────────
        # confidence 取排名第一的分数（整个检索应答的置信度）
        confidence = ranked_points[0][1]
        selected = ranked_points[:top_k]
        items = [self._item_response(point, score) for point, score in selected]
        knowledge_version = self._knowledge_version([point for point, _ in selected])

        if confidence >= self.settings.success_confidence_threshold:
            return self._response(
                request,
                status="success",
                answerable=True,
                confidence=confidence,
                queryRewrite=query_rewrite,
                items=items,
                knowledgeVersion=knowledge_version,
                started=started,
            )
        if confidence >= self.settings.low_confidence_threshold:
            return self._response(
                request,
                status="low_confidence",
                answerable=False,
                confidence=confidence,
                queryRewrite=query_rewrite,
                items=items,
                knowledgeVersion=knowledge_version,
                fallback=RagFallback(
                    reason="retrieval_confidence_below_threshold",
                    suggestedAction="answer_carefully_or_handoff",
                ),
                started=started,
            )
        return self._response(
            request,
            status="not_found",
            answerable=False,
            confidence=confidence,
            queryRewrite=query_rewrite,
            items=[],
            knowledgeVersion=knowledge_version,
            fallback=RagFallback(reason="no_relevant_knowledge", suggestedAction="clarify_or_handoff"),
            started=started,
        )

    def _error_response(
        self,
        request: RagQueryRequest,
        started: float,
        code: str,
        message: str,
        retryable: bool,
    ) -> RagQueryResponse:
        """构建错误响应。写入审计日志后返回 status=error 的响应。"""
        response = RagQueryResponse(
            requestId=request.requestId,
            traceId=request.traceId,
            status="error",
            answerable=False,
            confidence=0.0,
            queryRewrite=None,
            knowledgeVersion=None,
            items=[],
            error=RagError(code=code, message=message, retryable=retryable),
            fallback=RagFallback(reason="rag_unavailable", suggestedAction="safe_fallback"),
            latencyMs=int((time.perf_counter() - started) * 1000),
        )
        self._record_query(request, response)
        return response

    def _response(self, request: RagQueryRequest, started: float, **kwargs: Any) -> RagQueryResponse:
        """构建正常响应（success / low_confidence / not_found）。

        通过 **kwargs 传入动态字段，自动计算 latency_ms。
        每条响应都会写入审计日志。
        """
        response = RagQueryResponse(
            requestId=request.requestId,
            traceId=request.traceId,
            latencyMs=int((time.perf_counter() - started) * 1000),
            **kwargs,
        )
        self._record_query(request, response)
        return response

    def _record_query(self, request: RagQueryRequest, response: RagQueryResponse) -> None:
        """写入审计日志和（如适用）知识缺口事件。

        关键设计：
        - sessionId 和 userId 经 SHA-256 hash 后存储，不存明文。
        - query 和 originalQuery 经 PII 脱敏后存储。
        - not_found 和 low_confidence 的查询额外写入 gap_events 表。
        - 整个 try/except 包裹，写入失败静默返回，绝不影响 RAG 主链路。
        """
        try:
            salt = self.settings.rag_service_api_key
            top_knowledge_ids = [item.knowledgeId for item in response.items]
            top_chunk_ids = [item.chunkId for item in response.items]
            top_doc_ids = [item.source.docId for item in response.items if item.source.docId]
            # ── 写入审计日志 ──────────────────────────
            self.repository.create_audit_log(
                AuditLogRecord(
                    audit_id=new_id("audit"),
                    request_id=request.requestId,
                    trace_id=request.traceId,
                    session_id_hash=hash_identifier(request.sessionId, salt),
                    user_id_hash=hash_identifier(request.userId, salt),
                    channel=request.channel,
                    original_query_masked=mask_text(request.originalQuery),
                    query_masked=mask_text(request.query) or "",
                    intent=request.intent,
                    sub_intent=request.subIntent,
                    filters=request.filters.model_dump(),
                    status=response.status,
                    answerable=response.answerable,
                    confidence=response.confidence,
                    top_knowledge_ids=top_knowledge_ids,
                    top_chunk_ids=top_chunk_ids,
                    top_doc_ids=top_doc_ids,
                    knowledge_version=response.knowledgeVersion,
                    latency_ms=response.latencyMs,
                    error_code=response.error.code if response.error else None,
                )
            )
            # ── 写入知识缺口事件（仅 not_found / low_confidence）──
            if response.status in {"not_found", "low_confidence"}:
                self.repository.create_gap_event(
                    KnowledgeGapEventRecord(
                        gap_event_id=new_id("gap_event"),
                        request_id=request.requestId,
                        trace_id=request.traceId,
                        session_id_hash=hash_identifier(request.sessionId, salt),
                        user_id_hash=hash_identifier(request.userId, salt),
                        channel=request.channel,
                        original_query_masked=mask_text(request.originalQuery),
                        query_masked=mask_text(request.query) or "",
                        intent=request.intent,
                        sub_intent=request.subIntent,
                        filters=request.filters.model_dump(),
                        status=response.status,
                        confidence=response.confidence,
                        business_domain_guess=(request.filters.businessDomains or [None])[0],
                        knowledge_type_guess=(request.filters.knowledgeTypes or [None])[0],
                        top_candidate_knowledge_ids=top_knowledge_ids,
                    )
                )
        except Exception:
            # Audit logging must never break user-facing RAG responses.
            return

    def _rerank_text(self, payload: dict[str, Any]) -> str:
        """构建 rerank 模型的输入文本。

        拼接标题、摘要、关键词、相似问法、正文、允许表达。
        使用换行分隔各字段，末尾过滤掉仅含分隔符的空字段。
        """
        parts = [
            f"标题：{payload.get('title') or ''}",
            f"摘要：{payload.get('summary') or ''}",
            "关键词：" + "；".join(payload.get("keywords") or []),
            "相似问法：" + "；".join(payload.get("similarQuestions") or []),
            f"正文：{payload.get('content') or ''}",
            "允许表达：" + "；".join(payload.get("allowedClaims") or []),
        ]
        return "\n".join(part for part in parts if part.strip("："))

    def _query_signal_score(self, query: str, payload: dict[str, Any]) -> float:
        """计算查询与知识条目之间的文本信号分数。

        不依赖向量，而是基于字符级的精确匹配、子串匹配和 bigram 相似度。
        用于补充向量检索可能遗漏的精确关键词/相似问法匹配。

        打分策略（按优先级，命中即返回）：
        - 精确匹配（归一化后完全相等）: 0.92
        - 双向子串匹配（≥4 字符）: 0.88
        - 双字符 bigram Jaccard ≥ 0.55: 0.90
        - 双字符 bigram Jaccard ≥ 0.30: 0.78
        - 无匹配: 0.0

        Args:
            query: 改写后的查询文本。
            payload: Qdrant 存储的知识条目 payload。

        Returns:
            文本信号分数（0.0 ~ 0.92）。
        """
        candidates = [
            str(payload.get("title") or ""),
            *[str(value) for value in payload.get("keywords") or []],
            *[str(value) for value in payload.get("similarQuestions") or []],
        ]
        normalized_query = self._normalize_signal_text(query)
        if not normalized_query:
            return 0.0
        best_similarity = 0.0
        for candidate in candidates:
            normalized_candidate = self._normalize_signal_text(candidate)
            if not normalized_candidate:
                continue
            # 精确匹配（忽略大小写和标点）
            if normalized_query == normalized_candidate:
                return 0.92
            # candidate 是 query 的子串
            if len(normalized_candidate) >= 4 and normalized_candidate in normalized_query:
                return 0.88
            # query 是 candidate 的子串
            if len(normalized_query) >= 4 and normalized_query in normalized_candidate:
                return 0.88
            best_similarity = max(
                best_similarity,
                self._char_bigram_similarity(normalized_query, normalized_candidate),
            )
        if best_similarity >= 0.55:
            return 0.90
        if best_similarity >= 0.30:
            return 0.78
        return 0.0

    def _normalize_signal_text(self, value: str) -> str:
        """归一化文本：去除非字母数字字符，统一小写。

        用于在文本信号评分中做容错匹配。
        """
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def _char_bigram_similarity(self, left: str, right: str) -> float:
        """计算两个归一化字符串的字符级 bigram Jaccard 相似度。

        将字符串切分为相邻两个字符的集合，计算交集/并集比例。
        纯字符级，不需要分词器。

        Args:
            left: 归一化后的字符串。
            right: 归一化后的字符串。

        Returns:
            Jaccard 相似度（0.0 ~ 1.0）。至少一侧 < 2 字符时返回 0.0。
        """
        if left == right:
            return 1.0
        if len(left) < 2 or len(right) < 2:
            return 0.0
        left_grams = {left[index : index + 2] for index in range(len(left) - 1)}
        right_grams = {right[index : index + 2] for index in range(len(right) - 1)}
        if not left_grams or not right_grams:
            return 0.0
        return len(left_grams & right_grams) / len(left_grams | right_grams)

    def _item_response(self, point: Any, score: float) -> KnowledgeItemResponse:
        """从 Qdrant point 构建 KnowledgeItemResponse。

        从 payload 中提取所有字段，source 从嵌套 JSON 中还原。
        """
        payload = point.payload
        source = payload.get("source") or {}
        return KnowledgeItemResponse(
            knowledgeId=str(payload.get("knowledgeId") or ""),
            chunkId=str(payload.get("chunkId") or ""),
            title=str(payload.get("title") or ""),
            businessDomain=payload.get("businessDomain"),
            knowledgeType=payload.get("knowledgeType"),
            summary=str(payload.get("summary") or ""),
            content=str(payload.get("content") or ""),
            score=score,
            allowedClaims=list(payload.get("allowedClaims") or []),
            forbiddenClaims=list(payload.get("forbiddenClaims") or []),
            source=KnowledgeSource(**source),
            cards=[],
        )

    def _knowledge_version(self, points: list[Any]) -> str | None:
        """从检索结果中提取知识库版本号。

        取第一条命中 point 的 knowledgeVersion 字段。
        同一次检索的所有结果应属于同一版本（ingest 时统一设置）。
        """
        for point in points:
            value = (point.payload or {}).get("knowledgeVersion")
            if value:
                return str(value)
        return None

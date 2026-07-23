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
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
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
        started = time.perf_counter()
        top_k = min(request.topK or self.settings.rag_default_top_k, self.settings.rag_max_top_k)
        recall_limit = max(top_k, self.settings.rerank_top_n)
        query_rewrite = self.query_rewriter.rewrite(request)

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

        rerank_docs = [
            RerankDocument(id=str(point.payload.get("chunkId")), text=self._rerank_text(point.payload))
            for point in points
        ]
        try:
            rerank_results = self.rerank_client.rerank(query_rewrite, rerank_docs, top_n=top_k)
        except ModelProviderError as exc:
            return self._error_response(request, started, "rag_rerank_failed", str(exc), exc.retryable)
        point_by_chunk_id = {str(point.payload.get("chunkId")): point for point in points}
        ranked_points: list[tuple[Any, float]] = []
        for result in rerank_results:
            point = point_by_chunk_id.get(result.id)
            if point:
                score = max(result.score, self._query_signal_score(query_rewrite, point.payload))
                ranked_points.append((point, score))
        ranked_points.sort(key=lambda item: item[1], reverse=True)

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
        response = RagQueryResponse(
            requestId=request.requestId,
            traceId=request.traceId,
            latencyMs=int((time.perf_counter() - started) * 1000),
            **kwargs,
        )
        self._record_query(request, response)
        return response

    def _record_query(self, request: RagQueryRequest, response: RagQueryResponse) -> None:
        try:
            salt = self.settings.rag_service_api_key
            top_knowledge_ids = [item.knowledgeId for item in response.items]
            top_chunk_ids = [item.chunkId for item in response.items]
            top_doc_ids = [item.source.docId for item in response.items if item.source.docId]
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
            if normalized_query == normalized_candidate:
                return 0.92
            if len(normalized_candidate) >= 4 and normalized_candidate in normalized_query:
                return 0.88
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
        return "".join(ch.lower() for ch in value if ch.isalnum())

    def _char_bigram_similarity(self, left: str, right: str) -> float:
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
        for point in points:
            value = (point.payload or {}).get("knowledgeVersion")
            if value:
                return str(value)
        return None

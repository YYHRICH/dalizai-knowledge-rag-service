from __future__ import annotations

import time
from typing import Any

from apps.rag_service.app.core.config import Settings
from apps.rag_service.app.providers.dashscope import (
    DashScopeEmbeddingClient,
    DashScopeRerankClient,
    DashScopeSettings,
)
from apps.rag_service.app.providers.errors import ModelProviderError
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


class RagQueryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        model_settings = DashScopeSettings(
            api_key=settings.dashscope_api_key,
            embedding_base_url=settings.dashscope_embedding_base_url,
            rerank_base_url=settings.dashscope_rerank_base_url,
            embedding_model=settings.embedding_model,
            embedding_dimension=settings.embedding_dimension,
            rerank_model=settings.rerank_model,
        )
        self.embedding_client = DashScopeEmbeddingClient(model_settings)
        self.rerank_client = DashScopeRerankClient(model_settings)
        self.store = QdrantKnowledgeStore(
            QdrantStoreSettings(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                collection_alias=settings.qdrant_collection_alias,
                collection_prefix=settings.qdrant_collection_prefix,
                vector_size=settings.embedding_dimension,
            )
        )

    def query(self, request: RagQueryRequest) -> RagQueryResponse:
        started = time.perf_counter()
        top_k = min(request.topK or self.settings.rag_default_top_k, self.settings.rag_max_top_k)
        recall_limit = max(top_k, self.settings.rerank_top_n)
        query_rewrite = request.query

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
                ranked_points.append((point, result.score))

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
        return RagQueryResponse(
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

    def _response(self, request: RagQueryRequest, started: float, **kwargs: Any) -> RagQueryResponse:
        return RagQueryResponse(
            requestId=request.requestId,
            traceId=request.traceId,
            latencyMs=int((time.perf_counter() - started) * 1000),
            **kwargs,
        )

    def _rerank_text(self, payload: dict[str, Any]) -> str:
        parts = [
            f"标题：{payload.get('title') or ''}",
            f"摘要：{payload.get('summary') or ''}",
            f"正文：{payload.get('content') or ''}",
            "允许表达：" + "；".join(payload.get("allowedClaims") or []),
        ]
        return "\n".join(parts)

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

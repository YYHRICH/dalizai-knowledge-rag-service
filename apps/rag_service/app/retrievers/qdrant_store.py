"""Qdrant 向量库存储层。

封装 Qdrant 的检索、写入和管理操作。
Qdrant 在本项目中仅作为检索索引，不作为知识主库（主库是 Markdown + Git）。

关键设计：
- 检索始终通过 collection alias 访问，不直连实际 collection。
- 每次 ingest 创建新 collection，ingest 完成后原子切换 alias，实现零停机更新。
- point ID 基于 chunkId 的 UUID5 生成，同一条知识重复 ingest 时 ID 不变。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.rag_service.app.schemas.rag import RagFilters

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from apps.rag_service.app.ingestion.models import KnowledgeItem


@dataclass(frozen=True)
class QdrantStoreSettings:
    """Qdrant 连接和配置参数。"""

    url: str = "http://127.0.0.1:6333"
    """Qdrant 服务地址。"""

    api_key: str | None = None
    """Qdrant API Key（可选）。"""

    collection_alias: str = "dalizai_knowledge_v1"
    """检索时使用的 collection 别名。始终通过别名访问。"""

    collection_prefix: str = "dalizai_knowledge"
    """实际 collection 名称前缀。每次 ingest 创建 {prefix}_{timestamp} 的新 collection。"""

    vector_size: int = 1024
    """向量维度，需与 embedding 模型输出一致。"""

    distance: qmodels.Distance = qmodels.Distance.COSINE
    """向量相似度度量方式，默认余弦相似度。"""


class QdrantKnowledgeStore:
    """Qdrant 知识存储。

    提供向量检索、批量写入、collection 管理和 alias 切换功能。
    """
    def __init__(
        self,
        settings: QdrantStoreSettings,
        client: QdrantClient | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or QdrantClient(url=settings.url, api_key=settings.api_key or None)


    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        filters: RagFilters,
        limit: int,
        channel: str | None = None,
    ) -> list[Any]:
        """向量检索：在指定 collection 中查询最相似的 top-N 条记录。

        Args:
            collection_name: collection 名称（通常是 alias）。
            query_vector: 查询的 embedding 向量。
            filters: 业务域、知识类型、生效状态等过滤条件。
            limit: 返回的最大结果数。
            channel: 请求来源渠道，用于 scope 过滤。

        Returns:
            匹配的 Qdrant points 列表。
        """
        result = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=self._build_filter(filters, channel),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return list(result.points)

    def _build_filter(self, filters: RagFilters, channel: str | None = None) -> qmodels.Filter:
        """根据请求 filters 构建 Qdrant 查询过滤条件。

        过滤维度：
        1. businessDomains: 精确匹配（MatchAny）
        2. knowledgeTypes: 精确匹配（MatchAny）
        3. effectiveOnly: 仅返回 status=active 的记录
        4. scope 过滤: channels/cityCodes/stationIds — 允许全局（空数组）或定向匹配
        """
        must: list[qmodels.Condition] = []
        if filters.businessDomains:
            must.append(
                qmodels.FieldCondition(
                    key="businessDomain",
                    match=qmodels.MatchAny(any=filters.businessDomains),
                )
            )
        if filters.knowledgeTypes:
            must.append(
                qmodels.FieldCondition(
                    key="knowledgeType",
                    match=qmodels.MatchAny(any=filters.knowledgeTypes),
                )
            )
        if filters.effectiveOnly:
            must.append(qmodels.FieldCondition(key="status", match=qmodels.MatchValue(value="active")))

        # Scope filtering: global knowledge uses empty arrays. If request has a specific city/station,
        # allow both global and matching scoped knowledge. If not, only global knowledge is allowed.
        must.append(self._scope_condition("channels", channel))
        must.append(self._scope_condition("cityCodes", filters.cityCode))
        must.append(self._scope_condition("stationIds", filters.stationId))
        return qmodels.Filter(must=must)

    def _scope_condition(self, key: str, value: str | None) -> qmodels.Filter:
        """scope 匹配条件。

        策略：
        - 请求未传定向值（None）：只匹配全局知识（payload 中对应数组为空）。
        - 请求传了定向值：匹配全局知识 OR 包含该定向值的知识。

        例如，请求 cityCode=310000 时，能匹配：
        - cityCodes=[]（全局通用知识）
        - cityCodes 包含 310000（该城市的定向知识）
        但不匹配 cityCodes 包含 320000（其他城市的知识）。
        """
        if value:
            return qmodels.Filter(
                should=[
                    qmodels.IsEmptyCondition(is_empty=qmodels.PayloadField(key=key)),
                    qmodels.FieldCondition(key=key, match=qmodels.MatchAny(any=[value])),
                ]
            )
        return qmodels.Filter(must=[qmodels.IsEmptyCondition(is_empty=qmodels.PayloadField(key=key))])

    def recreate_collection(self, collection_name: str) -> None:
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=self.settings.vector_size,
                distance=self.settings.distance,
            ),
        )

    def upsert_items(
        self,
        collection_name: str,
        items: list[KnowledgeItem],
        vectors: list[list[float]],
        knowledge_version: str,
    ) -> None:
        """批量写入知识条目到 Qdrant（全量重建模式）。

        第一版采用全量重建：每次 ingest 创建全新 collection，
        upsert 所有知识条目，然后通过 switch_alias 原子切换。

        Args:
            collection_name: 目标 collection 名称（build collection）。
            items: 知识条目列表。
            vectors: 对应的向量列表，顺序必须与 items 一致。
            knowledge_version: 知识版本号，写入每条 point 的 payload。
        """
        if len(items) != len(vectors):
            raise ValueError("items and vectors length mismatch")
        points = [
            qmodels.PointStruct(
                id=self._point_id(item.chunk_id),
                vector=vector,
                payload=self._payload(item, knowledge_version),
            )
            for item, vector in zip(items, vectors, strict=True)
        ]
        if points:
            self.client.upsert(collection_name=collection_name, points=points)

    def count_points(self, collection_name: str) -> int:
        result = self.client.count(collection_name=collection_name, exact=True)
        return int(result.count)

    def switch_alias(self, collection_name: str) -> None:
        """原子切换 alias 到新 collection。

        先删除旧 alias，再创建指向新 collection 的 alias。
        在 Qdrant 中 alias 操作是事务性的，实现零停机更新。

        Args:
            collection_name: 新 build collection 的名称。
        """
        operations: list[qmodels.AliasOperations] = []
        aliases = self.client.get_aliases()
        for alias in aliases.aliases:
            if alias.alias_name == self.settings.collection_alias:
                operations.append(
                    qmodels.DeleteAliasOperation(
                        delete_alias=qmodels.DeleteAlias(alias_name=alias.alias_name)
                    )
                )
        operations.append(
            qmodels.CreateAliasOperation(
                create_alias=qmodels.CreateAlias(
                    collection_name=collection_name,
                    alias_name=self.settings.collection_alias,
                )
            )
        )
        self.client.update_collection_aliases(change_aliases_operations=operations)

    def _point_id(self, chunk_id: str) -> str:
        """基于 chunkId 生成确定性的 point ID。

        使用 UUID5（基于 URL namespace），确保同一 chunkId 每次 ingest
        生成相同 point ID。这保证了重新 ingest 时的幂等性。
        """
        import uuid

        return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

    def _payload(self, item: KnowledgeItem, knowledge_version: str) -> dict[str, Any]:
        metadata = item.document_metadata
        return {
            "knowledgeId": item.knowledge_id,
            "chunkId": item.chunk_id,
            "title": item.title,
            "businessDomain": item.business_domain,
            "knowledgeType": item.knowledge_type,
            "riskLevel": item.risk_level,
            "summary": item.summary,
            "content": item.content,
            "allowedClaims": item.allowed_claims,
            "forbiddenClaims": item.forbidden_claims,
            "keywords": item.keywords,
            "similarQuestions": item.similar_questions,
            "knowledgeVersion": knowledge_version,
            "status": metadata.get("status"),
            "ownerTeam": metadata.get("ownerTeam"),
            "owner": metadata.get("owner"),
            "effectiveFrom": metadata.get("effectiveFrom"),
            "effectiveTo": metadata.get("effectiveTo"),
            "updatedAt": metadata.get("updatedAt"),
            "reviewDueAt": metadata.get("reviewDueAt"),
            "channels": metadata.get("channels") or [],
            "cityCodes": metadata.get("cityCodes") or [],
            "stationIds": metadata.get("stationIds") or [],
            "source": {
                "docId": metadata.get("docId"),
                "docTitle": metadata.get("docTitle"),
                "section": item.title,
                "updatedAt": metadata.get("updatedAt"),
            },
        }

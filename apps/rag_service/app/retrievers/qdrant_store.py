from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from apps.rag_service.app.ingestion.models import KnowledgeItem


@dataclass(frozen=True)
class QdrantStoreSettings:
    url: str = "http://127.0.0.1:6333"
    api_key: str | None = None
    collection_alias: str = "dalizai_knowledge_v1"
    collection_prefix: str = "dalizai_knowledge"
    vector_size: int = 1024
    distance: qmodels.Distance = qmodels.Distance.COSINE


class QdrantKnowledgeStore:
    def __init__(
        self,
        settings: QdrantStoreSettings,
        client: QdrantClient | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or QdrantClient(url=settings.url, api_key=settings.api_key or None)

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
        # Qdrant point IDs can be UUIDs or unsigned integers. Use a stable UUID derived
        # from chunk_id so re-ingesting the same item into a build collection is deterministic.
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

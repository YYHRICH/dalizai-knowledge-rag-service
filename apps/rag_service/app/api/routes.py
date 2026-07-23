from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.rag_service.app.core.config import settings
from apps.rag_service.app.core.security import require_admin_api_key, require_service_api_key
from apps.rag_service.app.schemas.admin import (
    GapHandledStatus,
    KnowledgeGapClusterResponse,
    KnowledgeGapListResponse,
    UpdateKnowledgeGapStatusRequest,
    UpdateKnowledgeGapStatusResponse,
)
from apps.rag_service.app.retrievers import QdrantKnowledgeStore, QdrantStoreSettings
from apps.rag_service.app.schemas.rag import RagQueryRequest, RagQueryResponse
from apps.rag_service.app.services.rag_query_service import RagQueryService
from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase

router = APIRouter()


def get_metadata_repository() -> MetadataRepository:
    repository = MetadataRepository(SqliteDatabase(settings.rag_metadata_db_url))
    repository.initialize()
    return repository


def _cluster_response(row: dict) -> KnowledgeGapClusterResponse:
    return KnowledgeGapClusterResponse(
        clusterId=row["cluster_id"],
        representativeQuery=row["representative_query"],
        clusterTitle=row.get("cluster_title"),
        summary=row.get("summary"),
        businessDomainGuess=row.get("business_domain_guess"),
        knowledgeTypeGuess=row.get("knowledge_type_guess"),
        ownerTeam=row.get("owner_team"),
        eventCount=row["event_count"],
        statusBreakdown=row.get("status_breakdown") or {},
        topCandidateKnowledgeIds=row.get("top_candidate_knowledge_ids") or [],
        queryExamples=row.get("query_examples") or [],
        handledStatus=row["handled_status"],
        firstSeenAt=row["first_seen_at"],
        lastSeenAt=row["last_seen_at"],
        createdAt=row.get("created_at"),
        updatedAt=row.get("updated_at"),
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(
    _: None = Depends(require_admin_api_key),
    repository: MetadataRepository = Depends(get_metadata_repository),
) -> dict[str, object]:
    latest = repository.get_latest_successful_ingest_run()
    qdrant_status: dict[str, object]
    try:
        store = QdrantKnowledgeStore(
            QdrantStoreSettings(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                collection_alias=settings.qdrant_collection_alias,
                collection_prefix=settings.qdrant_collection_prefix,
                vector_size=settings.embedding_dimension,
            )
        )
        point_count = store.count_points(settings.qdrant_collection_alias)
        qdrant_status = {"status": "ok", "pointCount": point_count}
    except Exception as exc:
        qdrant_status = {"status": "error", "message": str(exc)[:200]}
    ready_status = bool(latest) and qdrant_status["status"] == "ok"
    return {
        "status": "ready" if ready_status else "not_ready",
        "latestIngest": latest,
        "qdrant": qdrant_status,
    }


@router.post("/v1/rag/query", response_model=RagQueryResponse)
def query_rag(
    request: RagQueryRequest,
    _: None = Depends(require_service_api_key),
) -> RagQueryResponse:
    service = RagQueryService(settings)
    return service.query(request)


@router.get("/v1/admin/knowledge-gaps", response_model=KnowledgeGapListResponse)
def list_knowledge_gaps(
    handledStatus: GapHandledStatus | None = Query(default="open"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin_api_key),
    repository: MetadataRepository = Depends(get_metadata_repository),
) -> KnowledgeGapListResponse:
    clusters = repository.list_gap_clusters(handledStatus, limit=limit, offset=offset)
    responses = [_cluster_response(cluster) for cluster in clusters]
    return KnowledgeGapListResponse(clusters=responses, count=len(responses))


@router.patch(
    "/v1/admin/knowledge-gaps/{cluster_id}/status",
    response_model=UpdateKnowledgeGapStatusResponse,
)
def update_knowledge_gap_status(
    cluster_id: str,
    request: UpdateKnowledgeGapStatusRequest,
    _: None = Depends(require_admin_api_key),
    repository: MetadataRepository = Depends(get_metadata_repository),
) -> UpdateKnowledgeGapStatusResponse:
    if repository.get_gap_cluster(cluster_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge gap cluster not found",
        )
    action_id = repository.update_gap_cluster_status(
        cluster_id,
        request.handledStatus,
        handled_by=request.handledBy,
        note=request.note,
    )
    return UpdateKnowledgeGapStatusResponse(
        actionId=action_id,
        clusterId=cluster_id,
        handledStatus=request.handledStatus,
    )

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.rag_service.app.core.config import settings
from apps.rag_service.app.core.security import require_admin_api_key, require_service_api_key
from apps.rag_service.app.schemas.rag import RagQueryRequest, RagQueryResponse
from apps.rag_service.app.services.rag_query_service import RagQueryService
from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(_: None = Depends(require_admin_api_key)) -> dict[str, object]:
    repository = MetadataRepository(SqliteDatabase(settings.rag_metadata_db_url))
    repository.initialize()
    latest = repository.get_latest_successful_ingest_run()
    return {
        "status": "ready" if latest else "not_ready",
        "latestIngest": latest,
    }


@router.post("/v1/rag/query", response_model=RagQueryResponse)
def query_rag(
    request: RagQueryRequest,
    _: None = Depends(require_service_api_key),
) -> RagQueryResponse:
    service = RagQueryService(settings)
    return service.query(request)

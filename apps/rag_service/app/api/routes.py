"""API 路由定义。

全部 HTTP 端点一览：

============ ====== ====================== ==================
端点          方法   鉴权                    用途
============ ====== ====================== ==================
/health       GET    无                     基本健康检查
/v1/health    GET    无                     详细就绪检查
/ready        GET    Admin API Key          完整健康 + 入库信息
/v1/rag/query POST   Service API Key        RAG 检索（Agent 调用）
/v1/admin/knowledge-gaps GET Admin API Key  查看缺口集群
/v1/admin/knowledge-gaps/:id/status PATCH Admin API Key 更新缺口状态
/v1/admin/eval-cases GET Admin API Key      查看评测用例
/v1/admin/debug/query POST Admin API Key    调试查询（带自动评测）
/debug        GET    无                     调试 HTML 页面
============ ====== ====================== ==================
"""

from __future__ import annotations

import uuid
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from apps.rag_service.app.core.config import settings
from apps.rag_service.app.core.security import require_admin_api_key, require_service_api_key
from apps.rag_service.app.evaluation.case_loader import (
    load_eval_cases_from_jsonl,
    load_eval_cases_from_knowledge,
)
from apps.rag_service.app.evaluation.evaluator import score_case
from apps.rag_service.app.evaluation.models import RagEvalCase
from apps.rag_service.app.schemas.admin import (
    GapHandledStatus,
    KnowledgeGapClusterResponse,
    KnowledgeGapListResponse,
    UpdateKnowledgeGapStatusRequest,
    UpdateKnowledgeGapStatusResponse,
)
from apps.rag_service.app.schemas.debug import (
    DebugQueryEvaluation,
    DebugQueryRequest,
    DebugQueryResponse,
    EvalCaseListResponse,
    EvalCaseResponse,
    EvalCaseSource,
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


def _eval_case_response(case: RagEvalCase) -> EvalCaseResponse:
    return EvalCaseResponse(
        id=case.id,
        query=case.query,
        expectedStatus=case.expected_status,
        shouldCallRag=case.should_call_rag,
        businessDomains=case.business_domains,
        knowledgeTypes=case.knowledge_types,
        expectedKnowledgeId=case.expected_knowledge_id,
        expectedContextIds=case.expected_context_ids,
        expectedClaims=case.expected_claims,
        negativeContextIds=case.negative_context_ids,
        channel=case.channel,
        intent=case.intent,
        subIntent=case.sub_intent,
        notes=case.notes,
    )


def _load_debug_eval_cases(source: EvalCaseSource, include_not_called: bool) -> list[RagEvalCase]:
    if source == "agent":
        cases = load_eval_cases_from_jsonl(Path("eval/agent_cases.jsonl"))
    elif source == "jsonl":
        cases = load_eval_cases_from_jsonl(Path("eval/cases.jsonl"))
    else:
        cases = load_eval_cases_from_knowledge(Path(settings.knowledge_base_dir))
    if include_not_called:
        return cases
    return [case for case in cases if case.should_call_rag and case.expected_status != "not_called"]


def _debug_evaluation(request: DebugQueryRequest, response: RagQueryResponse) -> DebugQueryEvaluation | None:
    if not request.expectedStatus:
        return None
    case = RagEvalCase(
        id=request.requestId or "debug_case",
        query=request.query,
        expected_status=request.expectedStatus,
        business_domains=request.filters.businessDomains or [],
        knowledge_types=request.filters.knowledgeTypes or [],
        expected_context_ids=request.expectedContextIds,
        expected_knowledge_id=request.expectedKnowledgeId,
        reference_answer=request.referenceAnswer,
        expected_claims=request.expectedClaims,
        negative_context_ids=request.negativeContextIds,
        channel=request.channel,
        intent=request.intent,
        sub_intent=request.subIntent,
    )
    result = score_case(case, response)
    return DebugQueryEvaluation(
        statusMatch=result.status_match,
        expectedContextHit=result.expected_context_hit,
        contextPrecision=result.context_precision,
        contextRecall=result.context_recall,
        faithfulnessProxy=result.faithfulness_proxy,
        responseRelevancyProxy=result.response_relevancy_proxy,
        score=result.score,
        passed=result.passed,
        retrievedContextIds=result.retrieved_context_ids,
        retrievedKnowledgeIds=result.retrieved_knowledge_ids,
    )


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


def _service_version() -> str:
    try:
        return version("dalizai-rag-service")
    except PackageNotFoundError:
        return "0.1.0"


def _readiness_status(repository: MetadataRepository) -> dict[str, object]:
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
        "service": "dalizai-rag-service",
        "version": _service_version(),
        "latestIngest": latest,
        "qdrant": qdrant_status,
    }


@router.get("/health")
def health() -> dict[str, str]:
    """基本健康检查。无鉴权，返回固定 JSON。"""
    return {"status": "ok"}


@router.get("/v1/health")
def v1_health(repository: MetadataRepository = Depends(get_metadata_repository)) -> dict[str, object]:
    """详细就绪检查。返回服务状态、Qdrant 连接和最新入库信息。"""
    return _readiness_status(repository)


@router.get("/ready")
def ready(
    _: None = Depends(require_admin_api_key),
    repository: MetadataRepository = Depends(get_metadata_repository),
) -> dict[str, object]:
    """管理员就绪检查（需 Admin API Key）。返回与 /v1/health 相同的信息。"""
    return _readiness_status(repository)


@router.post("/v1/rag/query", response_model=RagQueryResponse)
def query_rag(
    request: RagQueryRequest,
    _: None = Depends(require_service_api_key),
) -> RagQueryResponse:
    """RAG 检索（Agent 调用入口）。需 Service API Key Bearer Token 鉴权。"""
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
    """分页查询知识缺口集群。默认只返回 open 状态的集群。需 Admin API Key。"""
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
    """更新缺口集群的处理状态。同时写入操作审计记录。需 Admin API Key。"""
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


@router.get("/debug", include_in_schema=False)
def debug_page() -> FileResponse:
    """返回 RAG 调试控制台 HTML 页面。无需鉴权。"""
    return FileResponse(Path(__file__).resolve().parents[1] / "static" / "debug.html")


@router.get("/v1/admin/eval-cases", response_model=EvalCaseListResponse)
def list_eval_cases(
    source: EvalCaseSource = Query(default="knowledge"),
    includeNotCalled: bool = Query(default=False),
    _: None = Depends(require_admin_api_key),
) -> EvalCaseListResponse:
    """列出评测用例。支持 knowledge（内嵌）和 agent（JSONL）两个来源。需 Admin API Key。"""
    cases = _load_debug_eval_cases(source, includeNotCalled)
    responses = [_eval_case_response(case) for case in cases]
    return EvalCaseListResponse(source=source, cases=responses, count=len(responses))


@router.post("/v1/admin/debug/query", response_model=DebugQueryResponse)
def debug_query(
    request: DebugQueryRequest,
    _: None = Depends(require_admin_api_key),
) -> DebugQueryResponse:
    """执行调试查询并返回 RAG 结果 + 自动评测。需 Admin API Key。

    如果请求中包含期望值字段（expectedStatus、expectedContextIds 等），
    会同时运行评测并返回 DebugQueryEvaluation。
    """
    request_id = request.requestId or f"debug_{uuid.uuid4().hex}"
    trace_id = request.traceId or f"trace_{request_id}"
    rag_request = RagQueryRequest(
        requestId=request_id,
        traceId=trace_id,
        sessionId=request.sessionId,
        userId=request.userId,
        channel=request.channel,
        originalQuery=request.originalQuery,
        query=request.query,
        normalizedQueryHint=request.normalizedQueryHint,
        intent=request.intent,
        subIntent=request.subIntent,
        topK=request.topK,
        filters=request.filters,
        context=request.context,
    )
    response = RagQueryService(settings).query(rag_request)
    return DebugQueryResponse(
        requestId=request_id,
        traceId=trace_id,
        response=response,
        evaluation=_debug_evaluation(request, response),
    )

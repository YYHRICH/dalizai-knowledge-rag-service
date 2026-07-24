"""知识缺口聚类脚本。

将尚未分配的知识缺口事件按语义相似度聚类，归入已有集群或创建新集群。
支持 dry-run 模式预览结果和 --disable-llm 模式跳过 LLM 摘要生成。

用法：
    python scripts/cluster_gap_events.py                          # 默认聚类
    python scripts/cluster_gap_events.py --dry-run                # 仅预览
    python scripts/cluster_gap_events.py --disable-llm            # 仅用规则生成标题
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cluster unassigned RAG knowledge gap events.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum gap events to process.")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=None,
        help="Cosine similarity threshold for grouping gap queries.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview clusters without writing DB.")
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Use rule-based titles and summaries instead of DashScope chat completion.",
    )
    return parser


def main() -> int:
    from apps.rag_service.app.core.config import settings
    from apps.rag_service.app.governance.gap_clustering import GapClusteringService
    from apps.rag_service.app.providers.dashscope import (
        DashScopeChatClient,
        DashScopeEmbeddingClient,
        DashScopeSettings,
    )
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase

    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args()
    model_settings = DashScopeSettings(
        api_key=os.getenv("DASHSCOPE_API_KEY") or settings.dashscope_api_key,
        embedding_base_url=os.getenv("DASHSCOPE_EMBEDDING_BASE_URL")
        or settings.dashscope_embedding_base_url,
        rerank_base_url=os.getenv("DASHSCOPE_RERANK_BASE_URL") or settings.dashscope_rerank_base_url,
        chat_base_url=os.getenv("DASHSCOPE_CHAT_BASE_URL") or settings.dashscope_chat_base_url,
        embedding_model=os.getenv("EMBEDDING_MODEL") or settings.embedding_model,
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION") or settings.embedding_dimension),
        rerank_model=os.getenv("RERANK_MODEL") or settings.rerank_model,
        chat_model=os.getenv("GAP_CLUSTER_CHAT_MODEL") or settings.gap_cluster_chat_model,
    )
    repository = MetadataRepository(SqliteDatabase(settings.rag_metadata_db_url))
    repository.initialize()
    embedding_client = DashScopeEmbeddingClient(model_settings)
    summary_client = None if args.disable_llm else DashScopeChatClient(model_settings)
    service = GapClusteringService(
        repository=repository,
        embedding_client=embedding_client,
        summary_client=summary_client,
        similarity_threshold=args.similarity_threshold or settings.gap_cluster_similarity_threshold,
    )
    try:
        result = service.cluster_unassigned_events(
            limit=args.limit or settings.gap_cluster_batch_size,
            dry_run=args.dry_run,
        )
    finally:
        embedding_client.close()
        if summary_client is not None:
            summary_client.close()

    print(f"processedEvents={result.processed_events}")
    print(f"createdClusters={result.created_clusters}")
    print(f"updatedClusters={result.updated_clusters}")
    print(f"assignedEvents={result.assigned_events}")
    for cluster in result.clusters:
        print(
            "cluster "
            f"id={cluster.cluster_id} title={cluster.cluster_title} "
            f"events={len(cluster.event_ids)} total={cluster.event_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

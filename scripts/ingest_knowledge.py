"""Validate and ingest knowledge Markdown files into Qdrant."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and ingest knowledge Markdown files.")
    parser.add_argument(
        "--knowledge-dir",
        default=None,
        help="Knowledge base directory. Defaults to KNOWLEDGE_BASE_DIR or ./knowledge.",
    )
    parser.add_argument(
        "--require-eval-questions",
        action="store_true",
        help="Require Eval Questions for mock/evaluation datasets.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate Markdown files; do not call models or write Qdrant.",
    )
    return parser


def utc_now_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def batched(items: list, batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def main() -> int:
    from apps.rag_service.app.ingestion import (
        KnowledgeMarkdownParser,
        KnowledgeValidator,
        ValidationOptions,
    )
    from apps.rag_service.app.ingestion.embedding_text import build_embedding_text
    from apps.rag_service.app.providers.dashscope import DashScopeEmbeddingClient, DashScopeSettings
    from apps.rag_service.app.retrievers import QdrantKnowledgeStore, QdrantStoreSettings
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase
    from apps.rag_service.app.storage.repository import IngestRunRecord

    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args()
    knowledge_dir = Path(args.knowledge_dir or os.getenv("KNOWLEDGE_BASE_DIR") or "knowledge")

    started_at = utc_now_iso()
    version_suffix = utc_now_compact()
    knowledge_version = os.getenv("KNOWLEDGE_VERSION") or f"kb_{version_suffix}"
    collection_prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "dalizai_knowledge")
    collection_alias = os.getenv("QDRANT_COLLECTION_ALIAS", "dalizai_knowledge_v1")
    build_collection = f"{collection_prefix}_{version_suffix}"
    ingest_id = f"ingest_{version_suffix}"

    metadata_db_url = os.getenv("RAG_METADATA_DB_URL", "sqlite:///data/rag_service.db")
    repository = MetadataRepository(SqliteDatabase(metadata_db_url))
    repository.initialize()

    documents, parser_issues = KnowledgeMarkdownParser().parse_directory(knowledge_dir)
    report = KnowledgeValidator().validate(
        documents,
        parser_issues,
        ValidationOptions(require_eval_questions=args.require_eval_questions),
    )

    print(f"knowledgeDir={knowledge_dir}")
    print(f"documents={len(report.documents)}")
    print(f"items={report.item_count}")
    print(f"errors={len(report.errors)}")
    print(f"warnings={len(report.warnings)}")

    for issue in report.errors:
        prefix = f"ERROR {issue.path}"
        if issue.knowledge_id:
            prefix += f"#{issue.knowledge_id}"
        print(f"{prefix}: {issue.message}")
    for issue in report.warnings:
        prefix = f"WARNING {issue.path}"
        if issue.knowledge_id:
            prefix += f"#{issue.knowledge_id}"
        print(f"{prefix}: {issue.message}")

    if not report.ok:
        repository.create_ingest_run(
            IngestRunRecord(
                ingest_id=ingest_id,
                knowledge_version=knowledge_version,
                started_at=started_at,
                finished_at=utc_now_iso(),
                status="failed",
                total_docs=len(report.documents),
                total_knowledge_items=report.item_count,
                failed_items=report.item_count,
                error_message="validation failed",
                warnings=[issue.message for issue in report.warnings],
            )
        )
        return 1

    if args.validate_only:
        print("status=validated")
        return 0

    items = [item for document in report.documents for item in document.items]
    embedding_texts = [build_embedding_text(item) for item in items]

    settings = DashScopeSettings(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        embedding_base_url=os.getenv(
            "DASHSCOPE_EMBEDDING_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        rerank_base_url=os.getenv(
            "DASHSCOPE_RERANK_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-api/v1",
        ),
        embedding_model=os.getenv("EMBEDDING_MODEL", "qwen3.7-text-embedding"),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
        rerank_model=os.getenv("RERANK_MODEL", "qwen3-rerank"),
    )
    embedding_client = DashScopeEmbeddingClient(settings)
    vectors: list[list[float]] = []
    try:
        for batch in batched(embedding_texts, 20):
            result = embedding_client.embed_texts(batch)
            vectors.extend(result.embeddings)
    finally:
        embedding_client.close()

    store = QdrantKnowledgeStore(
        QdrantStoreSettings(
            url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
            api_key=os.getenv("QDRANT_API_KEY") or None,
            collection_alias=collection_alias,
            collection_prefix=collection_prefix,
            vector_size=settings.embedding_dimension,
        )
    )
    store.recreate_collection(build_collection)
    store.upsert_items(build_collection, items, vectors, knowledge_version)
    point_count = store.count_points(build_collection)
    if point_count != len(items):
        repository.create_ingest_run(
            IngestRunRecord(
                ingest_id=ingest_id,
                knowledge_version=knowledge_version,
                started_at=started_at,
                finished_at=utc_now_iso(),
                status="failed",
                total_docs=len(report.documents),
                total_knowledge_items=report.item_count,
                active_items=len(items),
                failed_items=len(items) - point_count,
                qdrant_collection=build_collection,
                qdrant_alias=collection_alias,
                error_message=f"point count mismatch: expected {len(items)}, got {point_count}",
                warnings=[issue.message for issue in report.warnings],
            )
        )
        print(f"ERROR pointCountMismatch expected={len(items)} actual={point_count}")
        return 1

    store.switch_alias(build_collection)
    status = "success_with_warnings" if report.warnings else "success"
    repository.create_ingest_run(
        IngestRunRecord(
            ingest_id=ingest_id,
            knowledge_version=knowledge_version,
            started_at=started_at,
            finished_at=utc_now_iso(),
            status=status,
            total_docs=len(report.documents),
            total_knowledge_items=report.item_count,
            active_items=len(items),
            skipped_items=0,
            failed_items=0,
            qdrant_collection=build_collection,
            qdrant_alias=collection_alias,
            warnings=[issue.message for issue in report.warnings],
        )
    )
    print(f"knowledgeVersion={knowledge_version}")
    print(f"qdrantCollection={build_collection}")
    print(f"qdrantAlias={collection_alias}")
    print(f"pointCount={point_count}")
    print(f"status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from pathlib import Path

import pytest
from qdrant_client.http import models as qmodels

from apps.rag_service.app.ingestion import KnowledgeMarkdownParser, KnowledgeValidator
from apps.rag_service.app.ingestion.embedding_text import build_embedding_text
from apps.rag_service.app.retrievers import QdrantKnowledgeStore, QdrantStoreSettings

ROOT = Path(__file__).resolve().parents[3]


def first_item(knowledge_id: str):
    documents, parser_issues = KnowledgeMarkdownParser().parse_directory(ROOT / "knowledge")
    report = KnowledgeValidator().validate(documents, parser_issues)
    assert report.ok
    items = [item for document in documents for item in document.items]
    return next(item for item in items if item.knowledge_id == knowledge_id)


def test_embedding_text_uses_allowed_claims_but_not_forbidden_claims() -> None:
    item = first_item("faq_charge_scan_001")

    text = build_embedding_text(item)

    assert "标题：怎么扫码充电？" in text
    assert "业务域：charging" in text
    assert "允许表达" in text
    assert "用户连接充电枪后，可以在小程序中扫码启动充电。" in text
    assert "可以绕过余额校验启动" not in text


def test_qdrant_payload_contains_response_fields() -> None:
    item = first_item("coupon_stack_001")
    store = QdrantKnowledgeStore(QdrantStoreSettings(vector_size=3), client=object())

    payload = store._payload(item, "kb_test")

    assert payload["knowledgeId"] == "coupon_stack_001"
    assert payload["chunkId"] == "coupon_stack_001#main"
    assert payload["businessDomain"] == "coupon"
    assert payload["knowledgeType"] == "coupon_policy"
    assert payload["riskLevel"] == "high"
    assert payload["knowledgeVersion"] == "kb_test"
    assert payload["source"]["docId"] == "doc_coupon_policy_v1"
    assert payload["allowedClaims"]
    assert payload["forbiddenClaims"]


def test_qdrant_upsert_rejects_vector_length_mismatch() -> None:
    item = first_item("coupon_stack_001")
    store = QdrantKnowledgeStore(QdrantStoreSettings(vector_size=3), client=object())

    with pytest.raises(ValueError, match="length mismatch"):
        store.upsert_items("collection", [item], [], "kb_test")


def test_qdrant_recreate_collection_uses_expected_vector_config() -> None:
    calls = {}

    class FakeClient:
        def recreate_collection(self, collection_name, vectors_config):
            calls["collection_name"] = collection_name
            calls["vectors_config"] = vectors_config

    store = QdrantKnowledgeStore(QdrantStoreSettings(vector_size=3), client=FakeClient())

    store.recreate_collection("build_collection")

    assert calls["collection_name"] == "build_collection"
    assert calls["vectors_config"].size == 3
    assert calls["vectors_config"].distance == qmodels.Distance.COSINE

import json

import httpx
import pytest

from apps.rag_service.app.providers.dashscope import (
    DashScopeChatClient,
    DashScopeEmbeddingClient,
    DashScopeRerankClient,
    DashScopeSettings,
)
from apps.rag_service.app.providers.errors import ModelProviderAuthError, ModelProviderBadRequestError
from apps.rag_service.app.providers.models import RerankDocument


def settings() -> DashScopeSettings:
    return DashScopeSettings(api_key="test-key", embedding_dimension=3)


def test_embedding_client_posts_expected_payload() -> None:
    seen_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request["url"] = str(request.url)
        seen_request["headers"] = dict(request.headers)
        seen_request["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen3.7-text-embedding",
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                ],
                "usage": {"total_tokens": 10},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    embedding_client = DashScopeEmbeddingClient(settings(), client)

    result = embedding_client.embed_texts(["怎么扫码充电？", "扫码充电操作步骤"])

    assert seen_request["url"].endswith("/compatible-mode/v1/embeddings")
    assert seen_request["headers"]["authorization"] == "Bearer test-key"
    assert seen_request["payload"]["model"] == "qwen3.7-text-embedding"
    assert seen_request["payload"]["dimensions"] == 3
    assert result.dimension == 3
    assert result.embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert result.usage == {"total_tokens": 10}


def test_embedding_client_rejects_empty_texts() -> None:
    embedding_client = DashScopeEmbeddingClient(settings(), httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))))

    with pytest.raises(ModelProviderBadRequestError):
        embedding_client.embed_texts([])


def test_rerank_client_maps_indices_back_to_document_ids() -> None:
    seen_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request["url"] = str(request.url)
        seen_request["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen3-rerank",
                "results": [
                    {"index": 1, "relevance_score": 0.92},
                    {"index": 0, "relevance_score": 0.21},
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rerank_client = DashScopeRerankClient(settings(), client)

    results = rerank_client.rerank(
        "卡券是否可以叠加？",
        [
            RerankDocument(id="faq_charge_scan_001#main", text="扫码充电操作步骤"),
            RerankDocument(id="coupon_stack_001#main", text="部分卡券不可叠加使用"),
        ],
        top_n=2,
    )

    assert seen_request["url"].endswith("/compatible-api/v1/reranks")
    assert seen_request["payload"]["model"] == "qwen3-rerank"
    assert seen_request["payload"]["documents"] == ["扫码充电操作步骤", "部分卡券不可叠加使用"]
    assert [(result.id, result.index, result.score) for result in results] == [
        ("coupon_stack_001#main", 1, 0.92),
        ("faq_charge_scan_001#main", 0, 0.21),
    ]


def test_rerank_client_returns_empty_for_no_documents() -> None:
    rerank_client = DashScopeRerankClient(settings(), httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))))

    assert rerank_client.rerank("query", []) == []


def test_provider_raises_auth_error() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(401, json={"error": {"message": "bad key"}})))
    embedding_client = DashScopeEmbeddingClient(settings(), client)

    with pytest.raises(ModelProviderAuthError):
        embedding_client.embed_texts(["hello"])


def test_chat_client_posts_expected_payload() -> None:
    seen_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request["url"] = str(request.url)
        seen_request["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen-turbo",
                "choices": [{"message": {"content": '{"title":"扫码失败","summary":"用户反馈二维码无法识别。"}'}}],
                "usage": {"total_tokens": 20},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    chat_client = DashScopeChatClient(settings(), client)

    result = chat_client.complete_json("system", "user")

    assert seen_request["url"].endswith("/compatible-mode/v1/chat/completions")
    assert seen_request["payload"]["model"] == "qwen-turbo"
    assert seen_request["payload"]["response_format"] == {"type": "json_object"}
    assert result.content == '{"title":"扫码失败","summary":"用户反馈二维码无法识别。"}'
    assert result.usage == {"total_tokens": 20}

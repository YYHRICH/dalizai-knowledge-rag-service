from types import SimpleNamespace

import pytest

from apps.rag_service.app.schemas.rag import RagFilters, RagQueryRequest
from apps.rag_service.app.services.query_rewriter import QueryRewriter


class FakeChatClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.system_prompt = None
        self.user_prompt = None

    def complete_json(self, system_prompt: str, user_prompt: str):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return SimpleNamespace(content=self.content)


def make_request(**overrides):
    values = {
        "requestId": "request_001",
        "traceId": "trace_001",
        "sessionId": "session_001",
        "channel": "wechat_mini_program",
        "query": "用户问题",
        "filters": RagFilters(),
    }
    values.update(overrides)
    return RagQueryRequest(**values)


def test_qwen_rewriter_uses_agent_context_and_returns_query_rewrite() -> None:
    chat = FakeChatClient('{"queryRewrite":"卡券无法使用原因；订单结算页未展示卡券"}')
    request = make_request(
        originalQuery="这个券咋用不了",
        query="这个券咋用不了",
        normalizedQueryHint="卡券无法使用原因",
        intent="coupon_service",
        subIntent="coupon_not_show",
        filters=RagFilters(businessDomains=["coupon"], knowledgeTypes=["coupon_policy", "faq"]),
        context={"pageContext": {"page": "order_checkout"}},
    )

    rewrite = QueryRewriter(chat).rewrite(request)

    assert rewrite == "卡券无法使用原因；订单结算页未展示卡券"
    assert "只输出 JSON" in chat.system_prompt
    assert "这个券咋用不了" in chat.user_prompt
    assert "normalizedQueryHint" in chat.user_prompt


def test_qwen_rewriter_accepts_list_output() -> None:
    chat = FakeChatClient('{"queryRewrite":["扫码充电操作步骤","连接充电枪后扫码启动充电"]}')
    request = make_request(query="第一次用这个桩怎么开始？")

    assert QueryRewriter(chat).rewrite(request) == "扫码充电操作步骤；连接充电枪后扫码启动充电"


def test_qwen_rewriter_falls_back_to_query_on_invalid_json() -> None:
    chat = FakeChatClient('不是 JSON')
    request = make_request(query="附近有休息区吗")

    assert QueryRewriter(chat).rewrite(request) == "附近有休息区吗"


def test_qwen_rewriter_can_raise_when_fallback_disabled() -> None:
    chat = FakeChatClient('不是 JSON')
    request = make_request(query="附近有休息区吗")

    with pytest.raises(ValueError):
        QueryRewriter(chat, fallback_on_error=False).rewrite(request)

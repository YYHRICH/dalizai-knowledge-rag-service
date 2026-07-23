from apps.rag_service.app.schemas.rag import RagFilters, RagQueryRequest
from apps.rag_service.app.services.query_rewriter import QueryRewriter


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


def test_coupon_hint_is_signal_not_replacement() -> None:
    request = make_request(
        originalQuery="这个券咋用不了",
        query="这个券咋用不了",
        normalizedQueryHint="卡券无法使用原因",
        intent="coupon_service",
        subIntent="coupon_not_show",
        filters=RagFilters(businessDomains=["coupon"], knowledgeTypes=["coupon_policy", "faq"]),
        context={"pageContext": {"page": "order_checkout"}},
    )

    rewrite = QueryRewriter().rewrite(request)

    assert rewrite.startswith("卡券无法使用原因")
    assert "卡券使用条件" in rewrite
    assert "订单结算页未展示卡券" in rewrite
    assert "这个券咋用不了" in rewrite


def test_charge_start_signal_rewrites_to_operation_terms() -> None:
    request = make_request(
        originalQuery="第一次用这个桩怎么开始？",
        query="第一次用这个桩怎么开始？",
        intent="faq",
        subIntent="charge_scan_guide",
        filters=RagFilters(businessDomains=["charging"], knowledgeTypes=["faq", "operation_guide"]),
    )

    rewrite = QueryRewriter().rewrite(request)

    assert "扫码充电操作步骤" in rewrite
    assert "连接充电枪后扫码启动充电" in rewrite
    assert "第一次用这个桩怎么开始？" in rewrite


def test_no_matching_rule_returns_query() -> None:
    request = make_request(query="附近有休息区吗")

    assert QueryRewriter().rewrite(request) == "附近有休息区吗"

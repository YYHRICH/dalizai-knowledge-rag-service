from __future__ import annotations

from typing import Any

from apps.rag_service.app.schemas.rag import RagQueryRequest


class QueryRewriter:
    """Deterministic query rewrite v1.

    Agent-provided normalizedQueryHint is treated as a retrieval signal, not as
    the final rewrite. The returned text is the RAG-owned queryRewrite used for
    embedding and rerank, and is exposed for observability/audit.
    """

    max_phrases = 8

    def rewrite(self, request: RagQueryRequest) -> str:
        phrases: list[str] = []
        self._add(phrases, request.normalizedQueryHint)

        signal = self._signal_text(request)
        domains = set(request.filters.businessDomains or [])
        intent_text = " ".join(value for value in [request.intent, request.subIntent] if value)

        if self._has_coupon_signal(signal, domains, intent_text):
            self._extend(
                phrases,
                [
                    "卡券无法使用原因",
                    "卡券使用条件",
                    "订单结算页未展示卡券",
                ],
            )
        if self._has_charge_start_signal(signal, domains, intent_text):
            self._extend(
                phrases,
                [
                    "扫码充电操作步骤",
                    "连接充电枪后扫码启动充电",
                    "设备二维码启动充电",
                ],
            )
        if self._has_charge_stop_signal(signal, domains, intent_text):
            self._extend(
                phrases,
                [
                    "结束充电操作步骤",
                    "当前充电订单页面结束充电",
                ],
            )
        if self._has_invoice_signal(signal, domains, intent_text):
            self._extend(phrases, ["发票开具入口和流程", "订单页面申请发票"])
        if self._has_refund_signal(signal, domains, intent_text):
            self._extend(phrases, ["退款到账时间规则", "退款进度需业务系统查询"])
        if self._has_device_qrcode_signal(signal, domains, intent_text):
            self._extend(phrases, ["设备二维码无法识别处理方法"])
        if self._has_compensation_signal(signal, domains, intent_text):
            self._extend(phrases, ["赔偿承诺边界", "赔偿补偿需人工审核"])
        if self._has_handoff_signal(signal, domains, intent_text):
            self._extend(phrases, ["转人工处理规则", "客服协助处理"])

        self._add(phrases, request.query)
        if not phrases:
            return request.query
        return "；".join(phrases[: self.max_phrases])

    def _signal_text(self, request: RagQueryRequest) -> str:
        context_text = self._flatten_context(request.context)
        values = [
            request.originalQuery,
            request.query,
            request.normalizedQueryHint,
            request.intent,
            request.subIntent,
            " ".join(request.filters.businessDomains or []),
            " ".join(request.filters.knowledgeTypes or []),
            context_text,
        ]
        return " ".join(value for value in values if value).lower()

    def _flatten_context(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._flatten_context(item) for item in value.values())
        if isinstance(value, list):
            return " ".join(self._flatten_context(item) for item in value)
        if value is None:
            return ""
        return str(value)

    def _has_coupon_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return (
            "coupon" in domains
            or "coupon" in intent_text
            or any(word in signal for word in ["券", "优惠券", "卡券"])
        ) and any(word in signal for word in ["用不了", "不能用", "没展示", "不显示", "看不到", "not_show"])

    def _has_charge_start_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return ("charging" in domains or "charge" in intent_text or "充电" in signal) and any(
            word in signal for word in ["扫码", "扫哪里", "开始", "启动", "第一次", "这个桩"]
        )

    def _has_charge_stop_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return ("charging" in domains or "charge" in intent_text or "充电" in signal) and any(
            word in signal for word in ["结束", "停止", "停充", "关掉"]
        )

    def _has_invoice_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return "invoice" in domains or "invoice" in intent_text or any(word in signal for word in ["发票", "开票"])

    def _has_refund_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return ("refund" in domains or "refund" in intent_text or "退款" in signal) and any(
            word in signal for word in ["退款", "到账", "多久", "进度"]
        )

    def _has_device_qrcode_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return ("device" in domains or "device" in intent_text or "二维码" in signal) and any(
            word in signal for word in ["二维码", "扫不出", "扫不出来", "识别", "扫不了"]
        )

    def _has_compensation_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return "customer_service" in domains or any(
            word in signal for word in ["赔偿", "补偿", "赔我", "免单", "发券", "compensation"]
        )

    def _has_handoff_signal(self, signal: str, domains: set[str], intent_text: str) -> bool:
        return (
            "customer_service" in domains
            or "handoff" in intent_text
            or any(word in signal for word in ["人工", "客服", "投诉", "转人工"])
        )

    def _extend(self, phrases: list[str], values: list[str]) -> None:
        for value in values:
            self._add(phrases, value)

    def _add(self, phrases: list[str], value: str | None) -> None:
        normalized = (value or "").strip()
        if normalized and normalized not in phrases:
            phrases.append(normalized)

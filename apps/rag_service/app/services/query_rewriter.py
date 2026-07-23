from __future__ import annotations

import json
from typing import Any, Protocol

from apps.rag_service.app.providers.errors import ModelProviderError
from apps.rag_service.app.schemas.rag import RagQueryRequest


class QueryRewriteChatClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> Any:
        ...


class QueryRewriter:
    """Qwen-backed query rewrite for the RAG retrieval chain."""

    def __init__(self, chat_client: QueryRewriteChatClient, *, fallback_on_error: bool = True) -> None:
        self.chat_client = chat_client
        self.fallback_on_error = fallback_on_error

    def rewrite(self, request: RagQueryRequest) -> str:
        try:
            result = self.chat_client.complete_json(
                self._system_prompt(),
                self._user_prompt(request),
            )
            rewrite = self._parse_rewrite(result.content)
        except (ModelProviderError, json.JSONDecodeError, TypeError, ValueError):
            if not self.fallback_on_error:
                raise
            return request.query
        return rewrite or request.query

    def _system_prompt(self) -> str:
        return (
            "你是独立知识 RAG 服务的 query rewrite 模块。"
            "你的任务是把用户问题改写为更适合知识库检索的中文检索句。"
            "必须只输出 JSON 对象，格式为 {\"queryRewrite\": \"...\"}。"
            "queryRewrite 输出 2 到 4 个短检索句，用中文分号连接，不要输出解释。"
            "短句应像知识库标题、FAQ 标题、规则名称或操作指引标题，而不是客服回复。"
            "如果 normalizedQueryHint 非空且与用户问题不冲突，必须把它作为第一个短句。"
            "必须结合 intent、subIntent、filters、context.pageContext，把口语问题补足成业务检索词。"
            "例如 page=order_checkout 且问题涉及卡券不可用，应包含 订单结算页未展示卡券。"
            "不要回答用户问题，不要做业务结论，不要编造具体订单、金额、退款、设备实时状态。"
            "优先保留用户原话中的关键实体、业务域、问题类型和页面上下文。"
        )

    def _user_prompt(self, request: RagQueryRequest) -> str:
        payload = {
            "originalQuery": request.originalQuery or request.query,
            "query": request.query,
            "normalizedQueryHint": request.normalizedQueryHint,
            "intent": request.intent,
            "subIntent": request.subIntent,
            "channel": request.channel,
            "filters": request.filters.model_dump(),
            "context": request.context,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _parse_rewrite(self, content: str) -> str:
        data = json.loads(content)
        value = data.get("queryRewrite") if isinstance(data, dict) else None
        if isinstance(value, list):
            value = "；".join(str(item).strip() for item in value if str(item).strip())
        if not isinstance(value, str):
            raise ValueError("queryRewrite must be a string or string list")
        rewrite = "；".join(part.strip() for part in value.replace(";", "；").split("；") if part.strip())
        if not rewrite:
            raise ValueError("queryRewrite cannot be empty")
        return rewrite[:300]

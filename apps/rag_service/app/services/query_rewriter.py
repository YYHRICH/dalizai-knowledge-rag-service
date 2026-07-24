"""Query Rewrite 模块。

在 RAG 检索前，将 Agent 传入的用户查询（可能是口语化、不完整的表达）
改写为更适合知识库向量检索的中文检索短句。

使用 DashScope Chat 模型（qwen-turbo），采用 JSON 模式输出。
改写失败时自动 fallback 到原始 query，不阻塞检索链路。
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from apps.rag_service.app.providers.errors import ModelProviderError
from apps.rag_service.app.schemas.rag import RagQueryRequest


class QueryRewriteChatClient(Protocol):
    """Query Rewrite 所需的 Chat Client 接口（Protocol，不依赖具体实现）。

    这样做是为了解耦：QueryRewriter 不依赖 DashScopeChatClient 的具体类型，
    只要任何有 ``complete_json`` 方法的对象都可以注入（便于测试 mock）。
    """
    def complete_json(self, system_prompt: str, user_prompt: str) -> Any:
        ...


class QueryRewriter:
    """Query Rewrite 改写器。

    调用 Qwen Chat 模型将用户口语查询改写为 2-4 个检索短句。
    改写失败时自动退回到原始 query（保证服务可用性高于改写质量）。
    """

    def __init__(self, chat_client: QueryRewriteChatClient, *, fallback_on_error: bool = True) -> None:
        """初始化改写器。

        Args:
            chat_client: Chat Completion 客户端（注入 DashScopeChatClient 或 mock）。
            fallback_on_error: True 时改写失败返回原始 query；False 时抛出异常。
        """
        self.chat_client = chat_client
        self.fallback_on_error = fallback_on_error

    def rewrite(self, request: RagQueryRequest) -> str:
        """对查询请求执行改写。

        流程：
        1. 构建 system prompt（定义改写任务）和 user prompt（包含查询上下文）。
        2. 调用 Chat API 获取 JSON 输出。
        3. 解析 JSON，提取 queryRewrite 字段。
        4. 异常时 fallback 到 request.query。

        Args:
            request: RAG 查询请求。

        Returns:
            改写后的检索句（2-4 个短句用中文分号连接），或原始 query。
        """
        try:
            result = self.chat_client.complete_json(
                self._system_prompt(),
                self._user_prompt(request),
            )
            rewrite = self._parse_rewrite(result.content)
        except (ModelProviderError, json.JSONDecodeError, TypeError, ValueError):
            # Chat API 异常或 JSON 解析失败时：fallback 到原始 query
            if not self.fallback_on_error:
                raise
            return request.query
        return rewrite or request.query

    def _system_prompt(self) -> str:
        """生成 system prompt：定义改写任务的角色、格式和约束。

        关键约束：
        - 只输出 JSON，不输出解释。
        - 短句风格像知识库标题（FAQ/规则/指引），不像是客服回复。
        - normalizedQueryHint（如存在且不冲突）必须作为第一个短句。
        - 结合 pageContext 补充业务检索词（如"订单结算页未展示卡券"）。
        - 不编造具体订单/金额/退款/设备状态。
        - 保留关键实体、业务域和问题类型。
        """
        return (
            "你是独立知识 RAG 服务的 query rewrite 模块。"
            "你的任务是把用户问题改写为更适合知识库检索的中文检索句。"
            "必须只输出 JSON 对象，格式为 {\"queryRewrite\": \"...\"}。"
            "queryRewrite 输出 2 到 4 个短检索句，用中文分号连接，不要输出解释。"
            ""
            "改写规则："
            "1. 短句必须是用户真实可能问出口的自然口语，或者知识库 FAQ 标题风格的问题。"
            "   正确示例：「怎么领优惠券」「卡券能叠加用吗」「优惠券用不了怎么办」"
            "   错误示例：「优惠券可用性」「卡券获取途径」「优惠券使用条件评估」"
            "2. 不要用书面术语、学术词汇、官方文件语言。用普通人说话的方式改写。"
            "3. 每个短句尽量包含一个完整的动作或问题，例如「怎么xxx」「能不能xxx」「xxx怎么办」。"
            "4. 如果 normalizedQueryHint 非空且与用户问题不冲突，必须把它作为第一个短句。"
            "5. 结合 intent、subIntent、filters、context.pageContext 把口语问题补足。"
            "   例如 page=order_checkout 且问题涉及卡券不可用，应包含「订单结算页没显示优惠券」。"
            "6. 不要回答用户问题，不要做业务结论，不要编造具体订单、金额、退款、设备实时状态。"
            "7. 保留用户原话中的关键实体和意图，用户原话本身可以作为其中一个短句。"
        )

    def _user_prompt(self, request: RagQueryRequest) -> str:
        """将 RAG 查询请求序列化为 user prompt 的 JSON 字符串。

        包含原始查询、归一化提示、意图、渠道、过滤条件和页面上下文，
        给模型足够信息来生成精准的检索句。
        """
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
        """从 Chat API 返回的 JSON 中解析 queryRewrite。

        容错处理：
        - 如果 queryRewrite 是数组，用中文分号连接。
        - 统一中文分号（替换英文分号）。
        - 截断到 300 字符（防止模型输出过长）。
        - 去掉空短句。

        Raises:
            ValueError: queryRewrite 为空或格式不正确。
        """
        data = json.loads(content)
        value = data.get("queryRewrite") if isinstance(data, dict) else None
        # 容错：如果模型输出的是数组，转成字符串
        if isinstance(value, list):
            value = "；".join(str(item).strip() for item in value if str(item).strip())
        if not isinstance(value, str):
            raise ValueError("queryRewrite must be a string or string list")
        # 统一分号为中文分号，去掉空字符串
        rewrite = "；".join(part.strip() for part in value.replace(";", "；").split("；") if part.strip())
        if not rewrite:
            raise ValueError("queryRewrite cannot be empty")
        return rewrite[:300]

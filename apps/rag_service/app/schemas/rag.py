"""RAG 查询接口的请求/响应 Schema。

定义了 Agent 调用 POST /v1/rag/query 的完整数据模型。
所有字段使用 camelCase 命名以保持 API JSON 风格一致。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ── 状态枚举 ────────────────────────────────────────────────

RagStatus = Literal["success", "low_confidence", "not_found", "error"]
"""RAG 检索状态：

- ``success``: confidence >= 0.75，Agent 可放心使用 allowedClaims 回复。
- ``low_confidence``: 0.50 <= confidence < 0.75，Agent 应谨慎回答或转人工。
- ``not_found``: confidence < 0.50 或无候选，Agent 应澄清或转人工。
- ``error``: RAG 或依赖异常，Agent 应安全兜底。
"""

# ── 请求模型 ────────────────────────────────────────────────


class RagFilters(BaseModel):
    """检索过滤条件。

    由 Agent 根据意图识别结果传入，用于缩小检索范围。
    所有字段均可选，未传表示不过滤。
    """

    businessDomains: list[str] | None = None
    """业务域过滤，如 ``["charging", "payment"]``。未传表示全部域。"""

    knowledgeTypes: list[str] | None = None
    """知识类型过滤，如 ``["faq", "refund_policy"]``。未传表示全部类型。"""

    effectiveOnly: bool = True
    """是否仅查询当前生效（active 且在有效期内）的知识。默认 True。"""

    cityCode: str | None = None
    """城市过滤（第一版弱实现，保留字段）。"""

    stationId: str | None = None
    """站点过滤（第一版弱实现，保留字段）。"""


class RagQueryRequest(BaseModel):
    """RAG 查询请求。

    Agent / MCP 调用 POST /v1/rag/query 时的请求体。
    """

    requestId: str
    """Agent 当前请求的唯一 ID，用于全链路追踪。"""

    traceId: str
    """分布式链路追踪 ID，贯穿 Agent → RAG → 模型服务。"""

    sessionId: str
    """会话 ID，RAG 侧会 hash 后存储，不存明文。"""

    userId: str | None = None
    """用户 ID，RAG 侧会 hash 后存储，不存明文。"""

    channel: str = "wechat_mini_program"
    """来源渠道，第一版固定为微信小程序。用于知识 scope 匹配。"""

    originalQuery: str | None = None
    """用户原始输入文本，未传时等同 query。"""

    query: str
    """Agent 传给 RAG 的查询文本，可能是用户原话或经过轻量处理。"""

    normalizedQueryHint: str | None = None
    """Agent 对明确意图给出的归一化提示，仅作为 RAG query rewrite 的辅助信号。"""

    intent: str | None = None
    """Agent 识别出的主意图，如 "faq"、"refund"。"""

    subIntent: str | None = None
    """Agent 识别出的子意图，如 "charge_scan_guide"。"""

    topK: int | None = Field(default=None, ge=1)
    """期望返回的知识条目数，默认 5，最大 10。"""

    filters: RagFilters = Field(default_factory=RagFilters)
    """检索过滤条件。"""

    context: dict[str, Any] = Field(default_factory=dict)
    """脱敏后的页面上下文，如 pageContext 等低风险信息。"""


# ── 响应模型 ────────────────────────────────────────────────


class KnowledgeSource(BaseModel):
    """知识条目的来源追溯信息。"""

    docId: str | None = None
    """来源文档 ID，对应 Markdown 文件 front matter 中的 docId。"""

    docTitle: str | None = None
    """来源文档标题。"""

    section: str | None = None
    """文档内的章节/条目标题。"""

    updatedAt: str | None = None
    """知识最后更新时间。"""


class KnowledgeItemResponse(BaseModel):
    """单条检索到的知识条目。

    包含知识全文、可用的声明、禁止的声明以及检索置信度。
    """

    knowledgeId: str
    """知识条目唯一 ID，如 ``faq_charge_scan_001``。"""

    chunkId: str
    """chunk 唯一 ID，如 ``faq_charge_scan_001#main``。"""

    title: str
    """知识条目标题。"""

    businessDomain: str | None = None
    """业务域，如 ``charging``、``refund``。"""

    knowledgeType: str | None = None
    """知识类型，如 ``faq``、``refund_policy``。"""

    summary: str
    """知识摘要，可用于快速判断相关性。"""

    content: str
    """知识正文，是 Agent 组织回复的参考依据。"""

    score: float
    """本条知识的最终置信度分数（rerank score 与文本信号加权后的结果）。"""

    allowedClaims: list[str]
    """允许表达列表：Agent 可以在回复中使用的、经过业务审核的陈述句。"""

    forbiddenClaims: list[str] = Field(default_factory=list)
    """禁止表达列表：Agent 不得使用的陈述句，通常是高风险或未经验证的说法。"""

    source: KnowledgeSource
    """来源追溯信息。"""

    cards: list[dict[str, Any]] = Field(default_factory=list)
    """卡片展示信息（第一版保留字段，暂不使用）。"""


class RagFallback(BaseModel):
    """RAG 无法正常返回时的兜底建议。"""

    reason: str
    """兜底原因，如 ``no_relevant_knowledge``、``rag_unavailable``。"""

    suggestedAction: str
    """建议 Agent 执行的动作，如 ``clarify_or_handoff``、``safe_fallback``。"""


class RagError(BaseModel):
    """RAG 错误详情。"""

    code: str
    """错误码，如 ``rag_embedding_failed``、``rag_qdrant_query_failed``。"""

    message: str
    """人类可读的错误描述。"""

    retryable: bool
    """是否建议 Agent 重试。True 表示可能是临时故障，False 表示需要修复后才可重试。"""


class RagQueryResponse(BaseModel):
    """RAG 查询响应。

    这是 POST /v1/rag/query 的完整响应体，Agent 根据 status 字段分流处理。
    """

    requestId: str
    """原请求 ID，用于关联请求和响应。"""

    traceId: str
    """原链路追踪 ID。"""

    status: RagStatus
    """检索状态：success / low_confidence / not_found / error。"""

    answerable: bool
    """Agent 是否可以基于返回结果回答用户问题。仅 success 状态为 True。"""

    confidence: float
    """整体检索置信度，取排名第一的知识条目的最终分数。"""

    queryRewrite: str | None = None
    """RAG 改写后的检索句，只用于观测和审计，Agent 不应把它当成业务结论。"""

    knowledgeVersion: str | None = None
    """知识库版本号，用于问题回溯时的版本定位。"""

    items: list[KnowledgeItemResponse] = Field(default_factory=list)
    """检索到的知识条目列表，按置信度降序排列。"""

    fallback: RagFallback | None = None
    """当 status 非 success 时的兜底建议。"""

    error: RagError | None = None
    """当 status=error 时的错误详情。"""

    latencyMs: int | None = None
    """RAG 服务端处理耗时（毫秒），不含网络传输时间。"""

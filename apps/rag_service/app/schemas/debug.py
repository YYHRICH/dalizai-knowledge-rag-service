"""RAG 调试控制台的 Schema。

提供调试查询、评测用例浏览的数据模型。
调试查询在一次请求中同时返回 RAG 原始结果和自动评测打分。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.rag_service.app.schemas.rag import RagFilters, RagQueryResponse

# ── 评测用例来源 ────────────────────────────────────────────

EvalCaseSource = Literal["knowledge", "agent", "jsonl"]
"""评测用例的数据来源：

- ``knowledge``: 从知识 Markdown 文件的 Eval Questions 字段加载。
- ``agent``: 从 ``eval/agent_cases.jsonl`` 文件加载。
- ``jsonl``: 从 ``eval/cases.jsonl`` 文件加载（125 条评测用例）。
"""

# ── 评测用例模型 ────────────────────────────────────────────


class EvalCaseResponse(BaseModel):
    """评测用例的只读响应。"""

    id: str
    """用例唯一 ID，来自 ``knowledgeId__eval_NN`` 或 JSONL 中的 id。"""

    query: str
    """测试查询文本。"""

    expectedStatus: str
    """期望的 RAG 返回状态，如 ``success``、``not_found``。"""

    shouldCallRag: bool = True
    """Agent 是否应该为此类问题调用 RAG。False 表示不应调用。"""

    businessDomains: list[str] = Field(default_factory=list)
    """查询时应用的业务域过滤。"""

    knowledgeTypes: list[str] = Field(default_factory=list)
    """查询时应用的知识类型过滤。"""

    expectedKnowledgeId: str | None = None
    """期望命中的知识 ID（宽松匹配：命中任意一条即可）。"""

    expectedContextIds: list[str] = Field(default_factory=list)
    """期望命中的 chunk ID 列表（精确匹配）。"""

    expectedClaims: list[str] = Field(default_factory=list)
    """期望返回结果中包含的关键声明（用于评估忠实度）。"""

    negativeContextIds: list[str] = Field(default_factory=list)
    """不应出现在检索结果中的 chunk ID（用于评估精确率）。"""

    channel: str = "wechat_mini_program"
    """模拟的渠道。"""

    intent: str | None = None
    """模拟的意图。"""

    subIntent: str | None = None
    """模拟的子意图。"""

    notes: str | None = None
    """用例备注。"""


class EvalCaseListResponse(BaseModel):
    """评测用例列表响应。"""

    source: EvalCaseSource
    """用例来源。"""

    cases: list[EvalCaseResponse]
    """用例列表。"""

    count: int
    """用例总数。"""


# ── 调试查询模型 ────────────────────────────────────────────


class DebugQueryRequest(BaseModel):
    """调试查询请求。

    扩展了标准 RAG 查询请求，增加了评测期望值字段。
    如果填写了期望值，调试终端会同时返回自动评测结果。
    """

    # RAG 查询基础字段
    requestId: str | None = None
    """可选请求 ID，不填则自动生成。"""

    traceId: str | None = None
    """可选链路 ID，不填则自动生成。"""

    sessionId: str = "debug_session"
    """调试会话 ID，默认为固定值。"""

    userId: str | None = None
    """模拟用户 ID。"""

    channel: str = "wechat_mini_program"
    """模拟渠道。"""

    originalQuery: str | None = None
    """用户原始表达。"""

    query: str
    """查询文本（必填）。"""

    normalizedQueryHint: str | None = None
    """归一化查询提示。"""

    intent: str | None = None
    """模拟意图。"""

    subIntent: str | None = None
    """模拟子意图。"""

    topK: int | None = Field(default=5, ge=1)
    """返回条数。"""

    filters: RagFilters = Field(default_factory=RagFilters)
    """检索过滤条件。"""

    context: dict[str, Any] = Field(default_factory=dict)
    """页面上下文。"""

    # 评测期望值（可选，填写则触发自动评测）
    expectedStatus: str | None = None
    """期望的 RAG 状态。"""

    expectedKnowledgeId: str | None = None
    """期望命中的知识 ID。"""

    expectedContextIds: list[str] = Field(default_factory=list)
    """期望命中的 chunk ID 列表。"""

    expectedClaims: list[str] = Field(default_factory=list)
    """期望的关键声明。"""

    negativeContextIds: list[str] = Field(default_factory=list)
    """不应出现的 chunk ID。"""

    referenceAnswer: str | None = None
    """参考答案，用于评测响应相关性。"""


class DebugQueryEvaluation(BaseModel):
    """单次调试查询的自动评测结果。"""

    statusMatch: bool
    """RAG 返回状态是否与期望一致。"""

    expectedContextHit: bool
    """是否至少命中一个期望的 chunk。"""

    contextPrecision: float
    """上下文精确率（命中的期望 chunk / 检索到的 chunk，考虑排名）。"""

    contextRecall: float
    """上下文召回率（命中的期望 chunk / 全部期望 chunk）。"""

    faithfulnessProxy: float
    """忠实度代理指标：期望声明被检索内容覆盖的比例。"""

    responseRelevancyProxy: float
    """相关性代理指标：检索内容与参考答案的术语重合度。"""

    score: float
    """综合评分：0.20*status + 0.25*precision + 0.25*recall + 0.15*faithfulness + 0.15*relevancy。"""

    passed: bool
    """是否通过评测：statusMatch=True 且 expectedContextHit=True 且 score >= 0.75。"""

    retrievedContextIds: list[str]
    """实际检索到的 chunk ID 列表。"""

    retrievedKnowledgeIds: list[str]
    """实际检索到的知识 ID 列表。"""


class DebugQueryResponse(BaseModel):
    """调试查询响应。

    包含原始 RAG 响应和可选的自动评测结果。
    """

    requestId: str
    """请求 ID。"""

    traceId: str
    """链路 ID。"""

    response: RagQueryResponse
    """RAG 服务返回的原始查询响应。"""

    evaluation: DebugQueryEvaluation | None = None
    """自动评测结果，仅当请求中填写了期望值时返回。"""

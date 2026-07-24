"""RAG 评测的数据模型。

定义了评测用例、评测结果、评测摘要和评测报告的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.rag_service.app.schemas.rag import RagQueryResponse


@dataclass(frozen=True)
class RagEvalCase:
    """一条 RAG 评测用例。

    定义了输入（查询、过滤条件）和期望输出（状态、命中的 chunk、关键声明）。
    """

    id: str
    """用例唯一 ID。知识内置评测为 ``{knowledgeId}__eval_{NN}``，agent 评测来自 JSONL。"""

    query: str
    """测试查询文本。"""

    expected_status: str
    """期望的 RAG 检索状态，如 ``success``、``not_found``。"""

    should_call_rag: bool = True
    """该场景下 Agent 是否应该调用 RAG。False 表示这类问题不应走 RAG。"""

    business_domains: list[str] = field(default_factory=list)
    """查询时应用的业务域过滤。"""

    knowledge_types: list[str] = field(default_factory=list)
    """查询时应用的知识类型过滤。"""

    expected_context_ids: list[str] = field(default_factory=list)
    """期望命中的 chunk ID 列表。"""

    expected_knowledge_id: str | None = None
    """期望命中的知识 ID（宽松匹配）。"""

    reference_answer: str | None = None
    """参考答案，用于评测响应相关性。"""

    expected_claims: list[str] = field(default_factory=list)
    """期望检索结果中包含的关键声明。"""

    negative_context_ids: list[str] = field(default_factory=list)
    """不应出现在检索结果中的 chunk ID。"""

    channel: str = "wechat_mini_program"
    """模拟渠道。"""

    intent: str | None = None
    """模拟意图。"""

    sub_intent: str | None = None
    """模拟子意图。"""

    notes: str | None = None
    """用例备注。"""


@dataclass(frozen=True)
class RagEvalCaseResult:
    """单条用例的评测结果。

    包含原始用例、RAG 响应和所有评测指标。
    """

    case: RagEvalCase
    """对应的评测用例。"""

    response: RagQueryResponse
    """RAG 服务返回的原始响应。"""

    status_match: bool
    """RAG 返回状态是否与期望一致。"""

    expected_context_hit: bool
    """是否至少命中了一个期望的 chunk。"""

    context_precision: float
    """上下文精确率：命中的期望 chunk 占检索结果的比例（考虑排名加权）。"""

    context_recall: float
    """上下文召回率：命中的期望 chunk 占全部期望 chunk 的比例。"""

    faithfulness_proxy: float
    """忠实度代理指标：期望声明被检索内容覆盖的比例。"""

    response_relevancy_proxy: float
    """相关性代理指标：检索内容与参考答案的术语重合度。"""

    score: float
    """综合评分：加权平均五个维度。"""

    retrieved_context_ids: list[str]
    """实际检索到的 chunk ID 列表。"""

    retrieved_knowledge_ids: list[str]
    """实际检索到的知识 ID 列表。"""

    @property
    def passed(self) -> bool:
        """是否通过评测。

        三个条件同时满足才算通过：
        1. status 匹配
        2. 至少命中一个期望 chunk
        3. 综合评分 >= 0.75
        """
        return self.status_match and self.expected_context_hit and self.score >= 0.75


@dataclass(frozen=True)
class RagEvalSummary:
    """评测汇总统计。

    所有指标都是各用例对应指标的平均值。
    """

    total: int
    """用例总数。"""

    passed: int
    """通过数。"""

    failed: int
    """未通过数。"""

    status_accuracy: float
    """状态匹配准确率。"""

    expected_context_hit_rate: float
    """期望 chunk 命中率。"""

    context_precision: float
    """平均上下文精确率。"""

    context_recall: float
    """平均上下文召回率。"""

    faithfulness_proxy: float
    """平均忠实度代理指标。"""

    response_relevancy_proxy: float
    """平均相关性代理指标。"""

    mean_score: float
    """平均综合评分。"""


@dataclass(frozen=True)
class RagEvalReport:
    """完整的评测报告。"""

    summary: RagEvalSummary
    """汇总统计。"""

    results: list[RagEvalCaseResult]
    """每条用例的详细结果。"""

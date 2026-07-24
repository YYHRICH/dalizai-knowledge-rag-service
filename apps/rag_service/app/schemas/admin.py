"""知识缺口管理的 Admin API Schema。

提供管理员查看和处理知识缺口集群的数据模型。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── 缺口处理状态 ────────────────────────────────────────────

GapHandledStatus = Literal["open", "planned", "resolved", "ignored"]
"""缺口集群的处理状态：

- ``open``: 未处理，需要关注。
- ``planned``: 已计划补充相关知识，但尚未入库。
- ``resolved``: 已补充知识并入库，问题已解决。
- ``ignored``: 确认无需处理（如超出知识范围的问题）。
"""

# ── 缺口集群响应 ────────────────────────────────────────────


class KnowledgeGapClusterResponse(BaseModel):
    """单个知识缺口集群。

    由多个相似的未命中/低置信度查询事件聚类而成，
    帮助运营团队发现知识盲区。
    """

    clusterId: str
    """集群唯一 ID。"""

    representativeQuery: str
    """代表性查询文本，最能概括本集群的用户问题。"""

    clusterTitle: str | None = None
    """LLM 生成的集群标题（不超过 20 字）。"""

    summary: str | None = None
    """LLM 生成的集群摘要（不超过 80 字）。"""

    businessDomainGuess: str | None = None
    """推测的业务域，基于事件中的 filter 信息。"""

    knowledgeTypeGuess: str | None = None
    """推测的知识类型，基于事件中的 filter 信息。"""

    ownerTeam: str | None = None
    """应负责处理的团队，基于业务域推测。"""

    eventCount: int
    """本集群包含的缺口事件总数。"""

    statusBreakdown: dict[str, int] = Field(default_factory=dict)
    """事件状态分布，如 ``{"not_found": 15, "low_confidence": 3}``。"""

    topCandidateKnowledgeIds: list[str] = Field(default_factory=list)
    """事件中最常被返回（但置信度不足）的知识 ID 列表。"""

    queryExamples: list[str] = Field(default_factory=list)
    """脱敏后的查询示例（最多 5 条）。"""

    handledStatus: GapHandledStatus
    """当前处理状态。"""

    firstSeenAt: str
    """首次出现该类型缺口的时间（ISO 8601）。"""

    lastSeenAt: str
    """最近一次出现的时间（ISO 8601）。"""

    createdAt: str | None = None
    """集群创建时间。"""

    updatedAt: str | None = None
    """集群最后更新时间。"""


class KnowledgeGapListResponse(BaseModel):
    """知识缺口集群列表响应。"""

    clusters: list[KnowledgeGapClusterResponse]
    """集群列表，按最近出现时间降序。"""

    count: int
    """当前返回的集群数量。"""


# ── 缺口状态更新 ────────────────────────────────────────────


class UpdateKnowledgeGapStatusRequest(BaseModel):
    """更新缺口集群处理状态的请求。"""

    handledStatus: GapHandledStatus
    """新的处理状态。"""

    handledBy: str | None = Field(default=None, max_length=100)
    """处理人标识。"""

    note: str | None = Field(default=None, max_length=500)
    """处理备注，如补充的知识 ID 或忽略原因。"""


class UpdateKnowledgeGapStatusResponse(BaseModel):
    """更新缺口集群处理状态的响应。"""

    actionId: str
    """本次操作的唯一 ID，用于审计追溯。"""

    clusterId: str
    """被更新的集群 ID。"""

    handledStatus: GapHandledStatus
    """更新后的处理状态。"""

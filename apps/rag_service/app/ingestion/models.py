"""知识摄取（Ingestion）的数据模型。

定义了从 Markdown 文件解析到入库校验全链路的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

IssueLevel = Literal["error", "warning"]
"""校验问题的严重等级。error 会阻止入库，warning 不会。"""


@dataclass(frozen=True)
class EvalQuestion:
    """内嵌在知识条目中的评测问题。

    从 Markdown 的 ``### Eval Questions`` 区块的 JSON 数组解析而来。
    每个评测问题定义了一条测试用例：用什么 query 查、期望命中哪个 chunk。
    """

    question: str
    """测试查询文本。"""

    reference_answer: str
    """参考答案，用于评测忠实度。"""

    expected_context_ids: list[str]
    """期望检索命中的 chunk ID 列表。"""

    expected_status: str
    """期望的 RAG 状态，如 ``success``、``not_found``。"""

    expected_claims: list[str]
    """期望检索结果中包含的关键声明。"""

    negative_context_ids: list[str] = field(default_factory=list)
    """不应出现在检索结果中的 chunk ID。"""

    notes: str | None = None
    """评测备注。"""


@dataclass(frozen=True)
class KnowledgeDocument:
    """从单个 Markdown 文件解析出的知识文档。

    一个文件对应一个文档，包含 YAML front matter 元信息和若干知识条目。
    """

    path: Path
    """文件的绝对路径。"""

    metadata: dict[str, Any]
    """YAML front matter 中解析出的文档级元信息。"""

    title: str | None
    """文档一级标题（# 开头）。"""

    items: list[KnowledgeItem]
    """文档中的知识条目列表，每个二级标题（## 开头）对应一条。"""


@dataclass(frozen=True)
class KnowledgeItem:
    """单条知识，对应 Markdown 中一个 ## 二级标题区块。

    每个区块包含摘要、正文、允许/禁止表达、关键词、相似问法等字段。
    chunk_id 约定为 ``{knowledgeId}#main``，表示为该知识的主 chunk。
    """

    knowledge_id: str
    """知识条目唯一 ID，来自二级标题中 ``|`` 之前的部分，如 ``faq_charge_scan_001``。"""

    chunk_id: str
    """chunk ID，约定为 ``{knowledgeId}#main``。第一版每条知识只有一个 chunk。"""

    title: str
    """知识标题，来自二级标题中 ``|`` 之后的部分。"""

    summary: str
    """知识摘要，用于快速理解和在 rerank 中作为关键字段。"""

    content: str
    """知识正文，Agent 组织回复的参考依据。"""

    allowed_claims: list[str]
    """允许表达列表：Agent 可以使用的、经过审核的陈述句。"""

    forbidden_claims: list[str]
    """禁止表达列表：Agent 不得使用的陈述句，用于高风险知识的红线性约束。"""

    keywords: list[str]
    """关键词列表，用于文本信号评分和 embedding 增强。"""

    similar_questions: list[str]
    """相似问法列表，用于文本信号评分和 FAQ 类知识的检索增强。"""

    eval_questions: list[EvalQuestion]
    """内嵌的评测问题列表。"""

    source_path: Path
    """来源 Markdown 文件的路径。"""

    document_metadata: dict[str, Any]
    """来源文档的 YAML front matter 元信息。"""

    # ── 派生属性 ─────────────────────────────────────────────

    @property
    def business_domain(self) -> str | None:
        """从文档元信息中提取业务域，如 ``charging``、``refund``。"""
        value = self.document_metadata.get("businessDomain")
        return str(value) if value is not None else None

    @property
    def knowledge_type(self) -> str | None:
        """从文档元信息中提取知识类型，如 ``faq``、``refund_policy``。"""
        value = self.document_metadata.get("knowledgeType")
        return str(value) if value is not None else None

    @property
    def risk_level(self) -> str:
        """从文档元信息中提取风险等级，默认 ``medium``。

        影响检索行为：高风险知识必须有 forbiddenClaims。
        """
        value = self.document_metadata.get("riskLevel") or "medium"
        return str(value)


@dataclass(frozen=True)
class ValidationIssue:
    """知识校验过程中发现的一个问题。"""

    level: IssueLevel
    """问题级别：error 或 warning。"""

    path: Path
    """问题所在的文件路径。"""

    message: str
    """问题描述。"""

    knowledge_id: str | None = None
    """问题关联的知识 ID（如适用）。"""


@dataclass(frozen=True)
class ValidationReport:
    """知识校验的完整报告。

    包含解析出的所有文档和校验过程中发现的问题。
    通过属性方法提供便捷的统计和判断。
    """

    documents: list[KnowledgeDocument]
    """校验通过（或仅有 warning）的文档。"""

    issues: list[ValidationIssue]
    """所有校验问题（含 error 和 warning）。"""

    @property
    def errors(self) -> list[ValidationIssue]:
        """仅返回 error 级别的问题。"""
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """仅返回 warning 级别的问题。"""
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def item_count(self) -> int:
        """所有文档中的知识条目总数。"""
        return sum(len(document.items) for document in self.documents)

    @property
    def ok(self) -> bool:
        """校验是否通过：无 error 则视为通过。"""
        return not self.errors

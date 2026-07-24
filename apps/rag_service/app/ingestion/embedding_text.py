"""Embedding 文本构造。

将知识条目的各字段拼接为一条可供向量化的文本。
拼接格式与 ``docs/knowledge_format_v0.1.md`` 中定义一致。
"""

from __future__ import annotations

from apps.rag_service.app.ingestion.models import KnowledgeItem


def build_embedding_text(item: KnowledgeItem) -> str:
    """将一条知识条目拼接为 embedding 输入文本。

    参与 embedding 的字段（按拼接顺序）：
    1. 标题
    2. 业务域
    3. 知识类型
    4. 摘要
    5. 关键词（可选，顿号连接）
    6. 相似问法（可选，分号连接）
    7. 正文
    8. 允许表达（可选，分号连接）

    注意：forbiddenClaims 不参与 embedding，仅作为安全约束返回给 Agent。

    Args:
        item: 待向量化的知识条目。

    Returns:
        拼接后的文本字符串。末尾的空字符串会被过滤掉。
    """
    parts: list[str] = [
        f"标题：{item.title}",
        f"业务域：{item.business_domain or ''}",
        f"知识类型：{item.knowledge_type or ''}",
        f"摘要：{item.summary}",
    ]
    if item.keywords:
        parts.append("关键词：" + "、".join(item.keywords))
    if item.similar_questions:
        parts.append("相似问法：" + "；".join(item.similar_questions))
    parts.append(f"正文：{item.content}")
    if item.allowed_claims:
        parts.append("允许表达：" + "；".join(item.allowed_claims))
    return "\n".join(part for part in parts if part.strip())

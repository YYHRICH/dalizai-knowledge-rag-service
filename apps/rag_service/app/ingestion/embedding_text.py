from __future__ import annotations

from apps.rag_service.app.ingestion.models import KnowledgeItem


def build_embedding_text(item: KnowledgeItem) -> str:
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

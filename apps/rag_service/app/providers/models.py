"""模型服务 Provider 的通用数据模型。

定义了 embedding、rerank、chat completion 三类模型调用的
请求参数和返回结果的标准化数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    """Embedding 模型调用结果。

    包含原始文本向量化后的所有信息。
    """

    model: str
    """实际使用的模型名称。"""

    dimension: int
    """向量的维度，应与配置中的 embedding_dimension 一致。"""

    embeddings: list[list[float]]
    """向量列表，顺序与输入文本一一对应。每个向量是浮点数列表，长度为 dimension。"""

    usage: dict | None = None
    """API 用量信息（token 数等），由模型服务返回，可能为 None。"""


@dataclass(frozen=True)
class RerankDocument:
    """Rerank 的输入文档。"""

    id: str
    """文档唯一标识，通常用 chunkId。结果中通过此 id 关联回原始文档。"""

    text: str
    """文档文本内容。"""


@dataclass(frozen=True)
class RerankResult:
    """Rerank 的单条结果。"""

    id: str
    """对应 RerankDocument 的 id。"""

    index: int
    """在原始输入文档列表中的位置（从 0 开始）。"""

    score: float
    """相关性分数，通常在 0~1 之间，分数越高越相关。"""


@dataclass(frozen=True)
class ChatCompletionResult:
    """Chat Completion 模型调用结果。

    用于 query rewrite 和缺口聚类摘要生成。
    目前仅支持 JSON 模式输出。
    """

    model: str
    """实际使用的模型名称。"""

    content: str
    """模型输出的文本内容（JSON 字符串）。"""

    usage: dict | None = None
    """API 用量信息，由模型服务返回，可能为 None。"""

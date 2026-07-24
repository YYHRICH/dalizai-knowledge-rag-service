"""全局配置模块。

通过 pydantic-settings 从项目根目录的 ``.env`` 文件加载所有配置项。
所有字段都有默认值，敏感信息（API Key）需要在部署时通过环境变量覆盖。

使用方式：直接导入 ``settings`` 单例即可。
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """大力仔知识 RAG 服务的全局配置。

    配置优先级：环境变量 > .env 文件 > 代码默认值。
    所有配置项的命名遵循小写下划线风格，pydantic-settings 会自动
    与大写下划线风格的环境变量做映射（如 ``RAG_SERVICE_API_KEY``）。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── RAG API 鉴权 ──────────────────────────────────────────

    rag_service_api_key: str = "CHANGE_ME_RAG_SERVICE_API_KEY"
    """Agent 调用 /v1/rag/query 时使用的 Bearer Token。部署时必须修改。"""

    rag_admin_api_key: str = "CHANGE_ME_RAG_ADMIN_API_KEY"
    """管理员调用 /v1/admin/* 和 /ready 端点时使用的 Bearer Token。部署时必须修改。"""

    # ── RAG 检索参数 ──────────────────────────────────────────

    rag_default_top_k: int = 5
    """默认返回的知识条目数，当请求未指定 topK 时使用。"""

    rag_max_top_k: int = 10
    """允许的最大 topK，防止单次查询返回过多结果。"""

    success_confidence_threshold: float = 0.50
    """成功阈值：confidence >= 此值时 status=success。RAG 仅提供检索依据，最终判断由 Agent 完成，因此阈值较低。"""

    low_confidence_threshold: float = 0.30
    """低置信度下限：confidence 在此值与 success_threshold 之间时 status=low_confidence。"""

    # ── Qdrant 向量库 ─────────────────────────────────────────

    qdrant_url: str = "http://127.0.0.1:6333"
    """Qdrant 服务地址，本地开发默认 127.0.0.1:6333，Docker 部署时通过环境变量覆盖。"""

    qdrant_api_key: str | None = None
    """Qdrant API Key，如果 Qdrant 开启了鉴权则填写。"""

    qdrant_collection_alias: str = "dalizai_knowledge_v1"
    """Qdrant collection 的别名，RAG 检索始终通过别名访问，不直连实际 collection。"""

    qdrant_collection_prefix: str = "dalizai_knowledge"
    """实际 collection 名称前缀，每次 ingest 会创建 {prefix}_{timestamp} 的新 collection。"""

    # ── DashScope 模型服务 ────────────────────────────────────

    dashscope_api_key: str = "CHANGE_ME_DASHSCOPE_API_KEY"
    """阿里云 DashScope API Key，用于 embedding / rerank / chat 三个服务。"""

    dashscope_embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """DashScope Embedding 兼容模式 API 地址。"""

    dashscope_rerank_base_url: str = "https://dashscope.aliyuncs.com/compatible-api/v1"
    """DashScope Rerank 兼容 API 地址。"""

    dashscope_chat_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """DashScope Chat Completion 兼容模式 API 地址，用于 query rewrite 和 gap 摘要生成。"""

    embedding_model: str = "qwen3.7-text-embedding"
    """Embedding 模型名称，通过 DashScope 兼容模式 API 调用。"""

    embedding_dimension: int = 1024
    """Embedding 向量维度，必须与所选模型的实际输出一致。"""

    rerank_model: str = "qwen3-rerank"
    """Rerank 模型名称，通过 DashScope 兼容 API 调用。"""

    rerank_top_n: int = 10
    """Rerank 的召回上限，检索时 recall_limit = max(topK, rerank_top_n)。"""

    query_rewrite_chat_model: str = "qwen-turbo"
    """Query rewrite 使用的 Chat 模型，轻量级即可。"""

    gap_cluster_chat_model: str = "qwen-turbo"
    """知识缺口聚类摘要生成的 Chat 模型，轻量级即可。"""

    gap_cluster_similarity_threshold: float = 0.82
    """缺口聚类时两段文本视为"同类"的余弦相似度最低值。"""

    gap_cluster_batch_size: int = 100
    """每次聚类任务最多处理多少个未分配缺口事件。"""

    # ── 元数据存储 ────────────────────────────────────────────

    rag_metadata_db_url: str = "sqlite:///data/rag_service.db"
    """SQLite 元数据库地址，存储审计日志、入库记录、知识缺口等。仅支持 sqlite:/// 前缀。"""

    knowledge_base_dir: str = "knowledge"
    """Markdown 知识库根目录，相对于项目根目录的路径。"""


# 全局配置单例，服务启动时自动加载 .env 文件
settings = Settings()

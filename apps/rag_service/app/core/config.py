from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rag_service_api_key: str = "CHANGE_ME_RAG_SERVICE_API_KEY"
    rag_admin_api_key: str = "CHANGE_ME_RAG_ADMIN_API_KEY"
    rag_default_top_k: int = 5
    rag_max_top_k: int = 10
    success_confidence_threshold: float = 0.75
    low_confidence_threshold: float = 0.50

    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_alias: str = "dalizai_knowledge_v1"
    qdrant_collection_prefix: str = "dalizai_knowledge"

    dashscope_api_key: str = "CHANGE_ME_DASHSCOPE_API_KEY"
    dashscope_embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_rerank_base_url: str = "https://dashscope.aliyuncs.com/compatible-api/v1"
    dashscope_chat_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "qwen3.7-text-embedding"
    embedding_dimension: int = 1024
    rerank_model: str = "qwen3-rerank"
    rerank_top_n: int = 10
    gap_cluster_chat_model: str = "qwen-turbo"
    gap_cluster_similarity_threshold: float = 0.82
    gap_cluster_batch_size: int = 100

    rag_metadata_db_url: str = "sqlite:///data/rag_service.db"
    knowledge_base_dir: str = "knowledge"


settings = Settings()

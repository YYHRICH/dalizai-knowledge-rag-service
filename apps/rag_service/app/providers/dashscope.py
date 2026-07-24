"""DashScope（阿里云灵积）模型服务 Provider。

通过 DashScope 兼容模式 API 提供三类模型服务：
- ``DashScopeEmbeddingClient``: 文本向量化（embedding），将知识/查询文本转为稠密向量。
- ``DashScopeRerankClient``: 重排序（rerank），对召回候选按与查询的相关性重新打分排序。
- ``DashScopeChatClient``: 对话补全（chat completion），用于 query rewrite 和缺口聚类摘要生成。

三个 client 共享同一套 Settings 和 HTTP 错误处理策略（``_handle_response`` / ``_extract_error_message``）。
第一版默认使用 DashScope 云 API，代码层保留 provider 抽象，后续可切换为本地模型。
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .errors import ModelProviderAuthError, ModelProviderBadRequestError, ModelProviderError
from .models import ChatCompletionResult, EmbeddingResult, RerankDocument, RerankResult


@dataclass(frozen=True)
class DashScopeSettings:
    """DashScope 模型服务的连接配置。

    三个 client 共享同一组配置。api_key 和 base_url 对所有服务通用，
    embedding/rerank/chat 使用不同的模型名称。
    """

    api_key: str
    """DashScope API Key，通过 HTTP Authorization: Bearer 头传递。"""

    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """Embedding 兼容模式 API 基础地址，对齐 OpenAI API 格式。"""

    rerank_base_url: str = "https://dashscope.aliyuncs.com/compatible-api/v1"
    """Rerank 兼容 API 基础地址。"""

    chat_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """Chat Completion 兼容模式 API 基础地址，对齐 OpenAI API 格式。"""

    embedding_model: str = "qwen3.7-text-embedding"
    """Embedding 模型名称。输出 1024 维向量。"""

    embedding_dimension: int = 1024
    """Embedding 输出维度，用于校验 API 返回值和创建 Qdrant collection。"""

    rerank_model: str = "qwen3-rerank"
    """Rerank 模型名称。支持 QA 模式。"""

    chat_model: str = "qwen-turbo"
    """Chat 模型名称，用于 query rewrite 和缺口摘要（轻量模型即可）。"""

    timeout_seconds: float = 60.0
    """HTTP 请求超时时间（秒）。"""


class DashScopeEmbeddingClient:
    """DashScope Embedding 客户端。

    将文本列表转为稠密向量，通过兼容模式 API（对齐 OpenAI Embeddings API）调用。
    支持批量请求，ingest 脚本中以 batch=20 分批调用。
    """

    def __init__(
        self,
        settings: DashScopeSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        """初始化 Embedding 客户端。

        Args:
            settings: DashScope 连接配置。
            http_client: 可选的自定义 httpx.Client，用于测试时注入 mock。
        """
        self.settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout_seconds)
        self._owns_client = http_client is None
        """是否由本实例创建了 http_client，关闭时需要判断。"""

    def close(self) -> None:
        """关闭 HTTP 客户端。仅当客户端由本实例创建时才关闭。"""
        if self._owns_client:
            self._client.close()

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        """将文本列表向量化。

        Args:
            texts: 待向量化的文本列表，不能为空。

        Returns:
            EmbeddingResult: 包含向量列表、模型名称、维度和用量。

        Raises:
            ModelProviderBadRequestError: texts 为空。
            ModelProviderError: 返回的向量数量或维度不正确。

        校验逻辑：
        1. 返回向量数 == 输入文本数。
        2. 每个向量维度 == 配置中的 embedding_dimension。
        """
        if not texts:
            raise ModelProviderBadRequestError("texts cannot be empty")
        response = self._client.post(
            f"{self.settings.embedding_base_url.rstrip('/')}/embeddings",
            headers=self._headers(),
            json={
                "model": self.settings.embedding_model,
                "input": texts,
                "dimensions": self.settings.embedding_dimension,
                "encoding_format": "float",
            },
        )
        data = self._handle_response(response)
        embeddings = [item.get("embedding") for item in data.get("data", [])]
        if len(embeddings) != len(texts) or any(not isinstance(value, list) for value in embeddings):
            raise ModelProviderError("Invalid embeddings response", retryable=True)
        dimensions = {len(value) for value in embeddings}
        if dimensions != {self.settings.embedding_dimension}:
            raise ModelProviderError(
                f"Unexpected embedding dimensions: {sorted(dimensions)}",
                retryable=True,
            )
        return EmbeddingResult(
            model=data.get("model") or self.settings.embedding_model,
            dimension=self.settings.embedding_dimension,
            embeddings=embeddings,
            usage=data.get("usage"),
        )

    def _headers(self) -> dict[str, str]:
        """构建 HTTP 请求头。使用 Bearer Token 鉴权。"""
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict:
        """统一的 HTTP 响应处理。

        按状态码分类处理错误：
        - 401/403: 鉴权失败 → ModelProviderAuthError（不可重试）
        - 400-499: 请求参数错误 → ModelProviderBadRequestError（不可重试）
        - 500+: 服务端错误 → ModelProviderError（可重试）

        Args:
            response: httpx 响应对象。

        Returns:
            解析后的 JSON 字典。

        Raises:
            ModelProviderAuthError: 鉴权失败。
            ModelProviderBadRequestError: 请求参数错误。
            ModelProviderError: 服务端临时故障。
        """
        if response.status_code in {401, 403}:
            raise ModelProviderAuthError()
        if 400 <= response.status_code < 500:
            raise ModelProviderBadRequestError(
                self._extract_error_message(response),
                status_code=response.status_code,
            )
        if response.status_code >= 500:
            raise ModelProviderError(
                self._extract_error_message(response),
                retryable=True,
                status_code=response.status_code,
            )
        return response.json()

    def _extract_error_message(self, response: httpx.Response) -> str:
        """从 HTTP 错误响应中提取人类可读的错误信息。

        兼容多种 API 错误格式（OpenAI 兼容格式、DashScope 原生格式），
        兜底返回响应体前 300 字符。
        """
        try:
            data = response.json()
        except ValueError:
            return response.text[:300] or "Model provider request failed"
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])
        return "Model provider request failed"


class DashScopeRerankClient:
    """DashScope Rerank 客户端。

    对召回候选文档按与查询的相关性重新排序。
    输入 query + documents，返回按相关性降序排列的结果列表。

    输出中的 index 对应输入 documents 列表的下标，
    通过 documents[index].id 关联回原始 chunk。
    """

    def __init__(
        self,
        settings: DashScopeSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        """初始化 Rerank 客户端。

        Args:
            settings: DashScope 连接配置。
            http_client: 可选的自定义 httpx.Client，用于测试时注入 mock。
        """
        self.settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        """关闭 HTTP 客户端。"""
        if self._owns_client:
            self._client.close()

    def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        """对文档列表重新排序。

        Args:
            query: 查询文本（已 rewrite 后的检索句）。
            documents: 候选文档列表，来自 Qdrant 的首次召回结果。
            top_n: 返回的前 N 条结果数。默认返回全部。

        Returns:
            按相关性分数降序排列的结果列表。

        Raises:
            ModelProviderBadRequestError: query 为空。
            ModelProviderError: API 返回格式异常或结果索引越界。

        注意：返回空列表如果 documents 为空 — 不视为错误。
        """
        if not query.strip():
            raise ModelProviderBadRequestError("query cannot be empty")
        if not documents:
            return []
        # 调用 DashScope Rerank API（兼容模式，非 OpenAI 格式）
        response = self._client.post(
            f"{self.settings.rerank_base_url.rstrip('/')}/reranks",
            headers=self._headers(),
            json={
                "model": self.settings.rerank_model,
                "query": query,
                "documents": [document.text for document in documents],
                "top_n": top_n or len(documents),
                "return_documents": False,
            },
        )
        data = self._handle_response(response)
        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            raise ModelProviderError("Invalid rerank response", retryable=True)
        results: list[RerankResult] = []
        for raw_result in raw_results:
            index = raw_result.get("index")
            score = raw_result.get("relevance_score", raw_result.get("score"))
            if not isinstance(index, int) or not isinstance(score, int | float):
                raise ModelProviderError("Invalid rerank result item", retryable=True)
            if index < 0 or index >= len(documents):
                raise ModelProviderError("Rerank result index out of range", retryable=True)
            # 通过 index 关联回原始 document 的 id（chunkId）
            results.append(
                RerankResult(
                    id=documents[index].id,
                    index=index,
                    score=float(score),
                )
            )
        return results

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code in {401, 403}:
            raise ModelProviderAuthError()
        if 400 <= response.status_code < 500:
            raise ModelProviderBadRequestError(
                self._extract_error_message(response),
                status_code=response.status_code,
            )
        if response.status_code >= 500:
            raise ModelProviderError(
                self._extract_error_message(response),
                retryable=True,
                status_code=response.status_code,
            )
        return response.json()

    def _extract_error_message(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:300] or "Model provider request failed"
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])
        return "Model provider request failed"


class DashScopeChatClient:
    """DashScope Chat Completion 客户端。

    用于需要 LLM 推理的轻量任务：Query Rewrite 和知识缺口聚类摘要。
    强制使用 JSON 模式输出（``response_format: json_object``），
    temperature=0.2 以保证输出的一致性和可解析性。
    """

    def __init__(
        self,
        settings: DashScopeSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        """初始化 Chat 客户端。

        Args:
            settings: DashScope 连接配置。
            http_client: 可选的自定义 httpx.Client，用于测试时注入 mock。
        """
        self.settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        """关闭 HTTP 客户端。"""
        if self._owns_client:
            self._client.close()

    def complete_json(self, system_prompt: str, user_prompt: str) -> ChatCompletionResult:
        """调用 Chat Completion API，返回 JSON 格式的输出。

        使用 low temperature (0.2) + JSON mode 保证输出格式稳定。

        Args:
            system_prompt: 系统提示词，定义任务角色和输出格式约束。
            user_prompt: 用户提示词，包含具体的输入数据（JSON 字符串）。

        Returns:
            ChatCompletionResult: 模型输出内容（content 字段为 JSON 字符串，需调用方解析）。

        Raises:
            ModelProviderError: API 返回为空或格式不正确。
        """
        response = self._client.post(
            f"{self.settings.chat_base_url.rstrip('/')}/chat/completions",
            headers=self._headers(),
            json={
                "model": self.settings.chat_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        data = self._handle_response(response)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelProviderError("Invalid chat completion response", retryable=True)
        message = choices[0].get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError("Empty chat completion content", retryable=True)
        return ChatCompletionResult(
            model=data.get("model") or self.settings.chat_model,
            content=content,
            usage=data.get("usage"),
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code in {401, 403}:
            raise ModelProviderAuthError()
        if 400 <= response.status_code < 500:
            raise ModelProviderBadRequestError(
                self._extract_error_message(response),
                status_code=response.status_code,
            )
        if response.status_code >= 500:
            raise ModelProviderError(
                self._extract_error_message(response),
                retryable=True,
                status_code=response.status_code,
            )
        return response.json()

    def _extract_error_message(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:300] or "Model provider request failed"
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])
        return "Model provider request failed"

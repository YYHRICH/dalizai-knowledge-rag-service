from __future__ import annotations

from dataclasses import dataclass

import httpx

from .errors import ModelProviderAuthError, ModelProviderBadRequestError, ModelProviderError
from .models import EmbeddingResult, RerankDocument, RerankResult


@dataclass(frozen=True)
class DashScopeSettings:
    api_key: str
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    rerank_base_url: str = "https://dashscope.aliyuncs.com/compatible-api/v1"
    embedding_model: str = "qwen3.7-text-embedding"
    embedding_dimension: int = 1024
    rerank_model: str = "qwen3-rerank"
    timeout_seconds: float = 60.0


class DashScopeEmbeddingClient:
    def __init__(
        self,
        settings: DashScopeSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
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


class DashScopeRerankClient:
    def __init__(
        self,
        settings: DashScopeSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        if not query.strip():
            raise ModelProviderBadRequestError("query cannot be empty")
        if not documents:
            return []
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

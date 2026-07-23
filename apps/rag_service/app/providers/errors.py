from __future__ import annotations


class ModelProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True, status_code: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class ModelProviderAuthError(ModelProviderError):
    def __init__(self, message: str = "Model provider authentication failed") -> None:
        super().__init__(message, retryable=False, status_code=401)


class ModelProviderBadRequestError(ModelProviderError):
    def __init__(self, message: str, *, status_code: int | None = 400) -> None:
        super().__init__(message, retryable=False, status_code=status_code)

"""模型服务 Provider 的异常类型。

定义了三层异常，帮助调用方判断错误的可恢复性：
- 鉴权错误：不可重试，需要修复 API Key 配置。
- 请求错误：不可重试，需要修复请求参数。
- 通用服务错误：可重试，可能是临时故障。
"""

from __future__ import annotations


class ModelProviderError(RuntimeError):
    """模型服务通用错误基类。

    所有与模型服务交互（embedding / rerank / chat）相关的异常
    都继承自此基类。

    Attributes:
        retryable: 是否建议调用方重试。True 表示可能是临时故障，
                    False 表示需要修复配置或参数后方可重试。
        status_code: HTTP 状态码，可能为 None。
    """

    def __init__(self, message: str, *, retryable: bool = True, status_code: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class ModelProviderAuthError(ModelProviderError):
    """模型服务鉴权失败错误。

    通常由 HTTP 401/403 触发，表示 API Key 无效或过期。
    不可重试，需要更新 API Key 配置。
    """

    def __init__(self, message: str = "Model provider authentication failed") -> None:
        super().__init__(message, retryable=False, status_code=401)


class ModelProviderBadRequestError(ModelProviderError):
    """模型服务请求参数错误。

    通常由 HTTP 4xx（非鉴权类）触发，表示请求格式或参数不合法。
    不可重试，需要修复请求参数。
    """

    def __init__(self, message: str, *, status_code: int | None = 400) -> None:
        super().__init__(message, retryable=False, status_code=status_code)

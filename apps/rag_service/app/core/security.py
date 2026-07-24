"""API 鉴权模块。

提供两个 FastAPI 依赖函数，通过 HTTP Bearer Token 控制访问权限。
- 服务密钥：供 Agent/MCP 调用 RAG 查询接口
- 管理员密钥：供运维人员访问管理端点和就绪检查
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import settings


def require_service_api_key(authorization: str | None = Header(default=None)) -> None:
    """验证 Agent 服务调用密钥。

    用于保护 POST /v1/rag/query 端点。
    从 HTTP ``Authorization: Bearer <token>`` 头部提取 token，
    与配置中的 ``RAG_SERVICE_API_KEY`` 比对。

    Args:
        authorization: HTTP Authorization 头部的值（FastAPI Header 自动注入）。

    Raises:
        HTTPException: 401，token 缺失或不匹配。
    """
    expected = f"Bearer {settings.rag_service_api_key}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def require_admin_api_key(authorization: str | None = Header(default=None)) -> None:
    """验证管理员密钥。

    用于保护 /ready、GET /v1/admin/*、POST /v1/admin/debug/query 等端点。
    从 HTTP ``Authorization: Bearer <token>`` 头部提取 token，
    与配置中的 ``RAG_ADMIN_API_KEY`` 比对。

    Args:
        authorization: HTTP Authorization 头部的值（FastAPI Header 自动注入）。

    Raises:
        HTTPException: 401，token 缺失或不匹配。
    """
    expected = f"Bearer {settings.rag_admin_api_key}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

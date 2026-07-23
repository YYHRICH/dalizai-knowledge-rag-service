from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import settings


def require_service_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.rag_service_api_key}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def require_admin_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.rag_admin_api_key}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

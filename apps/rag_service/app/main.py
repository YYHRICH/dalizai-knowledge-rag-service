"""RAG 服务应用入口。

创建 FastAPI 应用实例，注册路由。生产环境通过 uvicorn 启动：
``uvicorn apps.rag_service.app.main:app --host 0.0.0.0 --port 8100``
"""

from __future__ import annotations

from fastapi import FastAPI

from apps.rag_service.app.api.routes import router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。

    使用工厂函数模式，便于测试时创建独立的 app 实例。
    """
    app = FastAPI(title="Dalizai Knowledge RAG Service", version="0.1.0")
    app.include_router(router)
    return app


# 模块级 app 实例，uvicorn 通过 ``main:app`` 引用
app = create_app()

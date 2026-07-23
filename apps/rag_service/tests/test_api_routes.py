from fastapi.testclient import TestClient

from apps.rag_service.app.main import create_app


def test_health() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/rag/query",
        json={
            "requestId": "request_001",
            "traceId": "trace_001",
            "sessionId": "session_001",
            "channel": "wechat_mini_program",
            "query": "怎么扫码充电？",
        },
    )

    assert response.status_code == 401

"""Check DashScope embedding and rerank connectivity."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    from apps.rag_service.app.providers.dashscope import (
        DashScopeEmbeddingClient,
        DashScopeRerankClient,
        DashScopeSettings,
    )
    from apps.rag_service.app.providers.models import RerankDocument

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key or api_key.startswith("CHANGE_ME"):
        print("DASHSCOPE_API_KEY is not configured")
        return 2

    settings = DashScopeSettings(
        api_key=api_key,
        embedding_base_url=os.getenv(
            "DASHSCOPE_EMBEDDING_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        rerank_base_url=os.getenv(
            "DASHSCOPE_RERANK_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-api/v1",
        ),
        embedding_model=os.getenv("EMBEDDING_MODEL", "qwen3.7-text-embedding"),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
        rerank_model=os.getenv("RERANK_MODEL", "qwen3-rerank"),
    )

    embedding_client = DashScopeEmbeddingClient(settings)
    rerank_client = DashScopeRerankClient(settings)
    try:
        embedding_result = embedding_client.embed_texts(
            ["怎么扫码充电？", "用户连接充电枪后，可以通过小程序扫码启动充电。"]
        )
        print("embeddingStatus=ok")
        print(f"embeddingModel={embedding_result.model}")
        print(f"embeddingCount={len(embedding_result.embeddings)}")
        print(f"embeddingDimension={embedding_result.dimension}")

        rerank_results = rerank_client.rerank(
            "卡券是否可以叠加使用",
            [
                RerankDocument(
                    id="coupon_stack_001#main",
                    text="部分卡券不可叠加使用，具体以活动页面和订单结算页展示为准。",
                ),
                RerankDocument(
                    id="faq_charge_scan_001#main",
                    text="用户连接充电枪后，可以通过小程序扫码启动充电。",
                ),
            ],
            top_n=2,
        )
        print("rerankStatus=ok")
        for result in rerank_results:
            print(f"rerankResult id={result.id} score={result.score:.6f}")
    finally:
        embedding_client.close()
        rerank_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

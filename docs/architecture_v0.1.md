# 大力仔独立知识 RAG 服务架构 v0.1

## 定位

本项目是独立知识 RAG 服务，第一版主要服务 `dalizai-agent-service`，未来可复用于其他 Agent。服务不生成最终对客回复，只返回知识依据、候选片段、允许表达与禁止表达。

业务真值问题，例如订单金额、账户余额、退款进度、设备实时状态，必须由业务 MCP 查询。RAG 可辅助解释规则，但不产出实时业务事实。

## 核心链路

```text
dalizai-agent-service
  -> faq_knowledge_mcp
  -> POST /v1/rag/query
  -> rag_service
  -> DashScope embeddings API
  -> Qdrant topN recall
  -> DashScope rerank API
  -> topK structured knowledge response
```

## 技术选型

- API: Python 3.11+ + FastAPI + Pydantic v2
- Vector DB: Qdrant
- Embedding: DashScope `qwen3.7-text-embedding`, 1024 dimensions
- Reranker: DashScope `qwen3-rerank`, qa mode
- Knowledge source: Markdown
- Ingestion: explicit full rebuild command in v1

## 第一版服务

- `rag_service`: 对 Agent/MCP 提供 RAG 查询、管理查询、健康检查。
- `model provider`: 第一版默认 DashScope 云 API，代码层保留 provider 抽象。
- `qdrant`: 存储知识向量和 payload metadata。

## 知识治理

- 只有 `active` 且在有效期内的知识参与检索。
- 支持 `reviewDueAt`，用于提醒业务复核知识。
- 记录 `not_found` 和 `low_confidence` 查询，形成知识缺口列表。
- 第一版不提供在线编辑接口，知识编辑通过 Markdown + 提交 + ingest。

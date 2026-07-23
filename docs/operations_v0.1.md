# 运维与本地部署规划 v0.1

## 本地依赖

- Python 3.11+
- Docker Desktop
- Qdrant Docker 容器
- DashScope API Key

当前开发机没有 NVIDIA CUDA 环境，第一版不在本机部署 embedding/rerank 模型，默认调用 DashScope 云 API。

## 模型供应商

第一版默认配置：

```text
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=qwen3.7-text-embedding
EMBEDDING_DIMENSION=1024
RERANK_PROVIDER=dashscope
RERANK_MODEL=qwen3-rerank
RERANK_MODE=qa
RERANK_TOP_N=10
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

需要在 `.env` 中配置：

```text
DASHSCOPE_API_KEY=CHANGE_ME_DASHSCOPE_API_KEY
```

后续可扩展为本地模型、Jina、Cohere、OpenAI 或内部模型网关。

## Qdrant

第一版使用固定 collection：

```text
QDRANT_COLLECTION=dalizai_knowledge_v1
```

每次 ingest 全量重建 collection。后续需要灰度和回滚时，再设计多 collection 或 alias 切换。

## 健康检查

- `GET /health`: 应用进程存活。
- `GET /ready`: 检查 Qdrant 和模型 provider 是否可用。

## 管理接口

```http
GET /v1/admin/knowledge/review-due
GET /v1/admin/knowledge-gaps
```

管理接口使用独立 `RAG_ADMIN_API_KEY`，第一版只做查询，不做知识编辑。

## 日志隐私

- `userId`、`sessionId` 记录 hash。
- `query`、`originalQuery` 脱敏后记录。
- 请求审计日志保留 90 天。
- 知识缺口日志保留 180 天。
- 服务运行日志保留 30 天。
- 日志仅用于问题排查、服务质量评估、知识库建设和安全审计。

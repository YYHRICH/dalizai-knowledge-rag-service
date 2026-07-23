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
DASHSCOPE_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_RERANK_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1
```

需要在 `.env` 中配置：

```text
DASHSCOPE_API_KEY=CHANGE_ME_DASHSCOPE_API_KEY
```

后续可扩展为本地模型、Jina、Cohere、OpenAI 或内部模型网关。

## 知识源路线

第一版使用当前仓库的 `knowledge/` 目录作为知识源。生产知识变多后，建议拆出独立知识仓库，并通过 `KNOWLEDGE_BASE_DIR` 指向外部目录。

中后期建设知识维护平台时，数据库作为编辑、审核、版本和复核主库。RAG ingest 只读取已发布快照，Qdrant 只作为检索索引。

## Qdrant

第一版使用 alias 安全发布：

```text
QDRANT_COLLECTION_ALIAS=dalizai_knowledge_v1
QDRANT_COLLECTION_PREFIX=dalizai_knowledge
QDRANT_KEEP_COLLECTIONS=2
```

每次 ingest 创建新的实际 collection，例如 `dalizai_knowledge_20260723_1030`。校验成功后，将 alias `dalizai_knowledge_v1` 切到新 collection。失败时不切 alias，旧版本继续可用。

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

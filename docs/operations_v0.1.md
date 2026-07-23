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
GET /v1/admin/knowledge-gaps?handledStatus=open&limit=100&offset=0
PATCH /v1/admin/knowledge-gaps/{cluster_id}/status
```

`knowledge-gaps` 用于查看聚类后的待补知识问题，状态流转支持 `open`、`planned`、`resolved`、`ignored`。

管理接口使用独立 `RAG_ADMIN_API_KEY`，第一版只做治理状态流转，不做知识编辑。

## 知识缺口聚类

实时查询链路只记录 `not_found` / `low_confidence` 到 `knowledge_gap_events`，不做聚类，避免影响接口延迟。

建议通过定时任务运行：

```powershell
.\.venv\Scripts\python scripts\cluster_gap_events.py --limit 100
```

常用参数：

```text
--limit 100                    单次最多处理的未聚类事件数
--similarity-threshold 0.82     embedding 余弦相似度聚类阈值
--dry-run                       只预览，不写库
--disable-llm                   不调用小模型，使用规则标题和摘要
```

第一版聚类策略：

- 使用 DashScope embedding 对未聚类问题向量化。
- 优先归并到已有 open cluster；低于阈值则创建新 cluster。
- 使用 DashScope 小模型为 cluster 生成标题和摘要；失败时退回规则生成。
- 聚类完成后回写 `knowledge_gap_events.cluster_id`，业务人员后续围绕 cluster 补知识。

建议频率：前期每天 1 次；上线初期或高流量阶段可每小时 1 次。

## RAG 评测

评测脚本用于检索回归，不生成最终对客回答。第一版参考 Ragas 思路，输出以下指标：

- `statusAccuracy`: `success / low_confidence / not_found` 是否符合预期。
- `contextPrecision`: 召回上下文是否少噪声，越靠前命中越好。
- `contextRecall`: 期望上下文是否被召回。
- `faithfulnessProxy`: 返回知识是否覆盖评测集中的 `expectedClaims`。
- `responseRelevancyProxy`: RAG 返回的知识是否足以支撑参考回答。

从 Markdown `Eval Questions` 加载评测集：

```powershell
.\.venv\Scripts\python scripts\run_eval.py --knowledge-dir knowledge --fail-under 0.75
```

从独立 JSONL 加载评测集：

```powershell
.\.venv\Scripts\python scripts\run_eval.py --cases-jsonl eval\questions.jsonl --fail-under 0.75
```

报告默认写入 `eval/reports/`，该目录为本地运行产物，不提交到 Git。

## 日志隐私

- `userId`、`sessionId` 记录 hash。
- `query`、`originalQuery` 脱敏后记录。
- 请求审计日志保留 90 天。
- 知识缺口日志保留 180 天。
- 服务运行日志保留 30 天。
- 日志仅用于问题排查、服务质量评估、知识库建设和安全审计。

# 大力仔独立知识 RAG 服务设计书 v0.1

## 1. 项目定位

本项目是独立知识 RAG 服务，第一版主要服务 `dalizai-agent-service`，由主 Agent 侧的 `faq_knowledge_mcp` 统一调用。服务名称和架构按多知识类型、多 Agent 复用设计，不限定为 FAQ。

RAG 服务只负责返回知识依据、候选片段、允许表达和禁止表达，不直接生成最终对客回复。最终话术由 Reply Agent 基于工具结果生成。

订单金额、账户余额、退款进度、设备实时状态等实时业务真值不由 RAG 回答，必须由订单、账户、退款、充电平台等业务 MCP 查询。RAG 可以辅助解释规则，但不产出实时业务事实。

## 2. 第一版目标

第一版先打通一个稳定主链路：

```text
Agent -> faq_knowledge_mcp -> POST /v1/rag/query -> RAG -> Qdrant -> DashScope embedding/rerank -> 结构化知识结果
```

第一版必须具备：

- 标准查询接口 `/v1/rag/query`
- Markdown 知识库格式和校验规则
- 显式 ingest 入库流程
- Qdrant 向量检索
- DashScope embedding 和 rerank
- 置信度状态判断
- 知识有效期过滤
- 审计日志和知识缺口记录
- 待复核知识查询
- 基础评测集

第一版暂不做：

- 在线知识编辑接口
- 知识维护后台页面
- 自动审核发布流程
- 多 collection 灰度发布和回滚
- 图文/视频多模态检索
- RAG 自己生成最终答案

## 3. 服务边界

### 3.1 RAG 负责

- 接收 Agent 的知识查询请求
- 根据 `query`、`filters`、`channel` 检索知识
- 调用 embedding provider 生成查询向量
- 从 Qdrant 召回候选知识
- 调用 rerank provider 对候选重排
- 返回 `status`、`answerable`、`confidence`、`items`、`fallback`
- 返回 `allowedClaims` 和 `forbiddenClaims`
- 记录审计日志和知识缺口

### 3.2 RAG 不负责

- 不生成最终对客话术
- 不查询实时订单、余额、退款、设备状态
- 不承诺赔偿、法律判断或未发布活动
- 不直接决定前端页面跳转
- 第一版不提供在线编辑知识能力

## 4. 技术选型

| 模块 | 第一版选型 |
| --- | --- |
| API 服务 | Python 3.11+ + FastAPI + Pydantic v2 |
| 向量库 | Qdrant |
| Embedding | DashScope `qwen3.7-text-embedding` |
| Embedding 维度 | 1024 |
| Rerank | DashScope `qwen3-rerank` |
| Rerank 模式 | `qa` |
| 知识源 | Markdown 文件 |
| 配置 | `.env` / 环境变量 |
| 测试 | pytest + eval/questions.jsonl |
| 代码质量 | ruff |

模型层必须抽象为 provider，第一版默认 `dashscope`，后续可扩展本地模型、Jina、Cohere、OpenAI 或内部模型网关。

## 5. 项目结构

```text
E:\FAQ_RAG
  apps/
    rag_service/
      app/
        api/
        core/
        schemas/
        services/
        retrievers/
        ingestion/
        governance/
        privacy/
        logging/
      tests/
    model_service/          # 可选本地模型服务预留，第一版默认不启用
      app/
      tests/
  knowledge/
    charging/
      faq.md
      operation_guide.md
      troubleshooting.md
    payment/
      billing_policy.md
      coupon_policy.md
      refund_policy.md
    account/
      faq.md
    customer_service/
      handoff_guide.md
  eval/
    questions.jsonl
  scripts/
    ingest_knowledge.py
    review_due_report.py
    run_eval.py
  docs/
  docker-compose.yml
  pyproject.toml
  .env.example
  README.md
```

## 6. 知识组织

知识库按业务域组织。一个 Markdown 文件是一个知识集合，一个二级标题是一条知识。

核心 metadata 分两层：

- `businessDomain`: 业务域，例如 `charging`、`payment`、`coupon`、`refund`、`account`、`customer_service`
- `knowledgeType`: 知识类型，例如 `faq`、`operation_guide`、`billing_policy`、`coupon_policy`、`refund_policy`、`troubleshooting`、`handoff_guide`

一条知识默认生成一个 chunk 和一个 Qdrant point。`chunkId` 默认是 `knowledgeId#main`。过长知识后续允许按段落拆为多个 chunk。

## 7. 知识生命周期

文档级状态：

| 状态 | 是否入库 | 说明 |
| --- | --- | --- |
| `draft` | 否 | 草稿 |
| `reviewing` | 否 | 待审核 |
| `active` | 是 | 已发布 |
| `disabled` | 否 | 人工停用 |
| `expired` | 否 | 已过期 |
| `archived` | 否 | 已归档 |

第一版 ingest 只写入 `active` 且在有效期内的知识。

有效期规则：

- `effectiveFrom` 必填
- `effectiveTo` 可为空，表示长期有效
- `reviewDueAt` 必填，只用于复核提醒，不影响检索

旧知识不建议物理删除，优先停用、过期或归档，以便审计追溯。

## 8. 查询链路

```text
/v1/rag/query
  -> API Key 鉴权
  -> 请求 schema 校验
  -> query 规范化
  -> query 脱敏后记录审计日志
  -> DashScope embedding
  -> 构造 Qdrant filter
  -> Qdrant topN 召回
  -> DashScope rerank
  -> 截取 topK
  -> 置信度判断
  -> 结构化响应
  -> not_found/low_confidence 记录知识缺口
```

过滤规则：

- `filters.businessDomains` 可选，不传默认所有业务域
- `filters.knowledgeTypes` 可选，不传默认所有知识类型
- `filters.effectiveOnly` 默认 `true`
- `channel` 第一版支持 `wechat_mini_program`
- 文档 `channels` 为空表示通用
- `cityCode` / `stationId` 字段保留，第一版可弱实现

召回参数：

- `topK` 默认 5，最大 10
- `RERANK_TOP_N` 第一版默认 10
- 最终 `confidence` 以 rerank score 为主

## 9. 置信度和状态

第一版使用全局阈值：

| 条件 | 状态 |
| --- | --- |
| `confidence >= 0.75` | `success` |
| `0.50 <= confidence < 0.75` | `low_confidence` |
| `confidence < 0.50` | `not_found` |

后续预留按 `knowledgeType` 配置不同阈值。计费、退款、优惠、政策类知识可在评测后提高阈值。

`low_confidence` 处理建议：

- 普通 FAQ / 操作指引：可谨慎回答
- 计费 / 退款 / 优惠 / 活动政策：优先澄清或转人工
- 故障责任、赔偿、法律相关：不输出结论，转人工

## 10. Agent 使用约束

- Reply Agent 优先使用 `allowedClaims` 组织回复
- `content` 是知识正文参考，不是最终答案
- 高风险知识必须检查 `forbiddenClaims`
- RAG 结果不得替代业务 MCP 的实时真值
- `cards` 第一版保留字段，默认空数组，由 Agent/MCP adapter 决定是否展示

## 11. 错误处理

错误码第一版固定：

```text
rag_bad_request
rag_auth_failed
rag_embedding_unavailable
rag_embedding_failed
rag_rerank_unavailable
rag_rerank_failed
rag_qdrant_unavailable
rag_qdrant_query_failed
rag_service_timeout
rag_internal_error
```

RAG 尽量返回标准 JSON，不暴露内部堆栈、数据库地址、API Key 或原始异常细节。Agent 侧主要依赖 `retryable` 和 `fallback.suggestedAction` 做兜底。

## 12. 日志、审计和隐私

请求审计日志记录：

```text
requestId, traceId, sessionIdHash, userIdHash, channel,
originalQueryMasked, queryMasked, intent, subIntent, filters,
status, answerable, confidence, topKnowledgeIds, topChunkIds,
topDocIds, knowledgeVersion, latencyMs, errorCode, createdAt
```

隐私规则：

- `userId` 和 `sessionId` 只记录 hash
- `query` 和 `originalQuery` 脱敏后记录
- 命中的 `knowledgeId`、`chunkId`、`docId` 必须记录
- 请求审计日志保留 90 天
- 知识缺口日志保留 180 天
- 服务运行日志保留 30 天
- 日志仅用于问题排查、服务质量评估、知识库建设和安全审计

## 13. 知识缺口机制

当查询结果为 `not_found` 或 `low_confidence` 时，记录知识缺口。

第一版记录原始缺口，不自动聚类、不自动创建知识。后续可按 query embedding 做相似问题聚类，并在达到阈值后提醒业务补充知识。

缺口状态：

```text
open
reviewing
resolved
ignored
```

## 14. 管理接口

第一版提供查询类管理接口：

```http
GET /health
GET /ready
GET /v1/admin/knowledge/review-due
GET /v1/admin/knowledge-gaps
```

管理接口使用独立 `RAG_ADMIN_API_KEY`。第一版不提供知识编辑接口，知识编辑通过 Markdown + 提交 + ingest。

## 15. 入库流程

```text
业务人员修改 Markdown
  -> 提交到仓库
  -> 执行 ingest 命令
  -> 解析 Markdown
  -> 校验必填字段和唯一 ID
  -> 过滤非 active 或未生效知识
  -> DashScope embedding
  -> 全量重建 Qdrant collection
  -> 输出入库报告
```

第一版固定 collection：`dalizai_knowledge_v1`。每次 ingest 全量重建。后续如需灰度、回滚，再引入多 collection 或 alias 切换。

## 16. 测试和验收

第一版测试包括：

- Markdown 解析与校验测试
- RAG 查询接口测试
- 错误和兜底测试
- 固定样例知识库
- 小型评测集 `eval/questions.jsonl`

评测集字段：

```text
id, query, businessDomains, knowledgeTypes, expectedKnowledgeId, expectedStatus
```

## 17. 本地开发要求

当前开发机可用于 RAG 服务、Qdrant、小规模知识入库和接口联调。由于没有 NVIDIA GPU，第一版模型调用走 DashScope 云 API，不在本机部署 embedding/rerank 模型。

需要本地准备：

- Python 3.11+
- Docker Desktop
- DashScope API Key
- GitHub 仓库

## 18. 后续演进

- 知识维护平台：表单编辑、审核、发布、回滚
- 知识缺口聚类和业务提醒
- 按知识类型动态阈值
- 多 collection/alias 灰度发布
- 线上评测和命中率报表
- 多 Agent 调用方管理
- 图文/视频多模态知识检索

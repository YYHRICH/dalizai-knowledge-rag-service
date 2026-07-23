# Agent 与 RAG Docker 联调信息 v0.1

## 1. 服务启动

本仓库推荐用 Docker Compose 启动 Qdrant 和 RAG 服务：

```powershell
cd E:\FAQ_RAG
docker compose --profile app up -d
```

RAG 服务暴露端口：

```text
8100
```

Agent 访问地址：

```text
本机联调：http://127.0.0.1:8100
同一个 docker compose 网络内：http://rag-service:8100
```

检索接口需要 API Key：

```http
Authorization: Bearer ${RAG_SERVICE_API_KEY}
```

开发调试台和 admin 接口使用：

```http
Authorization: Bearer ${RAG_ADMIN_API_KEY}
```

## 2. Health Check

Agent 联调使用：

```http
GET /v1/health
```

返回示例：

```json
{
  "status": "ready",
  "service": "dalizai-rag-service",
  "version": "0.1.0",
  "latestIngest": {},
  "qdrant": {
    "status": "ok",
    "pointCount": 24
  }
}
```

约定：

- `status=ready` 表示已有成功入库记录，且 Qdrant alias 可查询。
- `status=not_ready` 表示未完成入库，或 Qdrant/alias 不可用。
- `/v1/health` 当前不需要鉴权，便于 Docker/Agent 探活。
- 旧的 `/health` 只表示进程存活，返回 `{ "status": "ok" }`。
- `/ready` 保留给管理员使用，需要 `RAG_ADMIN_API_KEY`。

## 3. 检索接口

```http
POST /v1/rag/query
Content-Type: application/json
Authorization: Bearer ${RAG_SERVICE_API_KEY}
```

## 4. 请求格式确认

Agent 侧示例字段可以接受。推荐请求：

```json
{
  "requestId": "request_001",
  "traceId": "trace_001",
  "sessionId": "session_001",
  "userId": "user_001",
  "channel": "wechat_mini_program",
  "originalQuery": "怎么扫码充电？",
  "query": "怎么扫码充电？",
  "normalizedQueryHint": "扫码充电操作步骤",
  "intent": "faq_service",
  "subIntent": "scan_charge_guide",
  "topK": 5,
  "filters": {
    "businessDomains": ["charging"],
    "knowledgeTypes": ["faq", "operation_guide"],
    "effectiveOnly": true
  },
  "context": {
    "userProfile": {},
    "slots": {},
    "pageContext": {}
  }
}
```

字段确认：

- `requestId/traceId/sessionId/query` 必填。
- `userId/sessionId` 主要用于日志审计，RAG 侧 hash 后存储。
- `intent/subIntent` 可选，但建议传，Qwen query rewrite 会使用这些信号。
- `normalizedQueryHint` 可选，Agent 很确定时传；RAG 仍负责最终 `queryRewrite`。
- `filters.knowledgeTypes` 支持。
- `filters.businessDomains` 支持，强烈建议传，减少跨域误召回。
- `topK` 支持，默认 5，最大 10。
- `context` 可以为空对象；不要传手机号、身份证、订单明细、余额等敏感或实时业务真值。

## 5. 返回格式确认

可以返回 Agent 期望字段：

```text
status
answerable
confidence
queryRewrite
knowledgeVersion
items
items[].knowledgeId
items[].chunkId
items[].title
items[].businessDomain
items[].knowledgeType
items[].summary
items[].content
items[].score
items[].allowedClaims
items[].forbiddenClaims
items[].source
items[].cards
latencyMs
```

说明：

- RAG 不组织最终话术，只返回知识依据和可用/禁用声明。
- Agent 应优先基于 `allowedClaims` 组织回复，并检查 `forbiddenClaims`。
- `queryRewrite` 由 RAG 侧 Qwen 小模型生成，仅用于观测和审计，不是业务结论。

## 6. 状态码约定

业务状态：

```text
success          命中且可回答
low_confidence   命中但置信度低
not_found        未命中
error            RAG 依赖或服务异常
```

HTTP 状态：

```text
200  正常返回 success / low_confidence / not_found / error
422  请求 JSON 格式或字段校验失败
401  鉴权失败
500  未捕获服务异常
```

第一版暂未实现业务限流，所以暂不返回 `429`。

## 7. 超时与失败

Agent 侧建议：

```text
RAG_SERVICE_TIMEOUT_MS=3000
```

当前链路包含 Qwen query rewrite、embedding、Qdrant、rerank。云模型网络波动会影响耗时，联调期建议先按 3000ms 配置，后续通过观测数据再定 P95。

失败建议：

- `error.retryable=true` 可短重试一次。
- `not_found/low_confidence/error` 不允许编造，走澄清、业务 MCP、转人工或安全兜底。
- 首次启动后需要先完成知识入库；`/v1/health.status=ready` 后再跑检索联调。

## 8. 模拟数据集入库

当前模拟数据集 Markdown 格式可以入库。仓库内已放在：

```text
data/rag_mock_dataset_v0.1/knowledge
```

当前正式知识目录是：

```text
knowledge
```

确认项：

- `knowledgeId` 入库后保持不变。
- 当前一条知识默认一个 chunk，`chunkId={knowledgeId}#main`。
- `Eval Questions` 只用于评测集构造，不进入正式知识检索内容。
- Front Matter 字段可以解析；第一版条目继承文档级 Front Matter。

## 9. 联调测试问题

模拟知识库应覆盖以下问题：

```text
怎么扫码充电？
怎么结束充电？
可以预约充电吗？
二维码扫不出来怎么办？
充电枪拔不下来怎么办？
停车费怎么算？
充电费用怎么计算？
优惠券能不能叠加？
退款一般多久到账？
怎么申请发票？
登录不上怎么办？
在哪里查看历史订单？
我要找人工客服。
这个故障你们是不是一定要赔我？
```

具体命中结果建议在调试台验证：

```text
http://127.0.0.1:8100/debug
```

## 10. Agent 最关键 5 点回复

1. RAG Docker 地址：本机 `http://127.0.0.1:8100`，Compose 内部 `http://rag-service:8100`。
2. 检索接口：`POST /v1/rag/query`。
3. 返回字段：能对齐 Agent 期望格式，并额外返回 `allowedClaims/forbiddenClaims/source/queryRewrite/latencyMs`。
4. Markdown 模拟数据集：可以入库，当前格式已支持。
5. `chunkId`：第一版稳定为 `{knowledgeId}#main`。

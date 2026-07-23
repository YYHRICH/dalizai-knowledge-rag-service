# 大力仔 Agent 调用独立知识 RAG 接口协议 v0.2

## 1. 接口定位

本接口是 `dalizai-agent-service` 通过 `faq_knowledge_mcp` 调用独立知识 RAG 服务的稳定契约。RAG 服务返回知识依据和可用声明，不生成最终对客回复。

第一版接口只要求打通：

```http
POST /v1/rag/query
Content-Type: application/json
Authorization: Bearer ${RAG_SERVICE_API_KEY}
```

## 2. Request

```json
{
  "requestId": "request_202607230001",
  "traceId": "trace_202607230001",
  "sessionId": "session_001",
  "userId": "user_001",
  "channel": "wechat_mini_program",
  "originalQuery": "我不会弄那个充电，扫哪里啊",
  "query": "我不会弄那个充电，扫哪里啊",
  "normalizedQueryHint": "扫码充电操作步骤",
  "intent": "faq",
  "subIntent": "charge_scan_guide",
  "topK": 5,
  "filters": {
    "businessDomains": ["charging"],
    "knowledgeTypes": ["faq", "operation_guide"],
    "effectiveOnly": true,
    "cityCode": null,
    "stationId": null
  },
  "context": {}
}
```

## 3. 请求字段约定

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `requestId` | string | 是 | Agent 当前请求 ID |
| `traceId` | string | 是 | 全链路 Trace ID |
| `sessionId` | string | 是 | 会话 ID，RAG 日志中 hash 存储 |
| `userId` | string | 否 | 用户 ID，RAG 日志中 hash 存储 |
| `channel` | string | 是 | 第一版固定支持 `wechat_mini_program` |
| `originalQuery` | string | 否 | 用户原始表达，未传时视为等同 `query` |
| `query` | string | 是 | Agent 传给 RAG 的查询文本，可以是用户原话或轻量处理后的文本 |
| `normalizedQueryHint` | string | 否 | Agent 对明确意图给出的归一化提示，只作为 RAG query rewrite 的辅助信号，不替代 RAG 改写 |
| `intent` | string | 否 | Agent 识别出的主意图 |
| `subIntent` | string | 否 | Agent 识别出的子意图 |
| `topK` | integer | 否 | 默认 5，最大 10 |
| `filters` | object | 否 | 检索过滤条件 |
| `context` | object | 否 | 脱敏后的低风险上下文 |

`filters` 约定：

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `businessDomains` | string[] | 全部 | 业务域过滤，例如 `charging`、`coupon`、`payment` |
| `knowledgeTypes` | string[] | 全部 | 知识类型过滤，例如 `faq`、`operation_guide`、`coupon_policy` |
| `effectiveOnly` | boolean | `true` | 是否只查询当前生效知识 |
| `cityCode` | string/null | null | 城市字段保留，第一版弱实现 |
| `stationId` | string/null | null | 站点字段保留，第一版弱实现 |

## 4. Success Response

```json
{
  "requestId": "request_202607230001",
  "traceId": "trace_202607230001",
  "status": "success",
  "answerable": true,
  "confidence": 0.86,
  "queryRewrite": "扫码充电操作步骤；连接充电枪后扫码启动充电；我不会弄那个充电，扫哪里啊",
  "knowledgeVersion": "kb_2026_07_23_1000",
  "items": [
    {
      "knowledgeId": "faq_charge_scan_001",
      "chunkId": "faq_charge_scan_001#main",
      "title": "怎么扫码充电？",
      "businessDomain": "charging",
      "knowledgeType": "faq",
      "summary": "用户连接充电枪后，可以通过小程序扫码启动充电。",
      "content": "用户连接充电枪后，可在小程序首页点击扫码充电，扫描设备二维码并确认启动。",
      "score": 0.86,
      "allowedClaims": [
        "用户连接充电枪后，可以在小程序中扫码启动充电。"
      ],
      "forbiddenClaims": [
        "一定可以启动成功。"
      ],
      "source": {
        "docId": "doc_charging_faq_v1",
        "docTitle": "充电常见问题",
        "section": "怎么扫码充电？",
        "updatedAt": "2026-07-23T00:00:00+08:00"
      },
      "cards": []
    }
  ],
  "latencyMs": 128
}
```

## 5. Not Found / Low Confidence

未命中：

```json
{
  "requestId": "request_202607230002",
  "traceId": "trace_202607230002",
  "status": "not_found",
  "answerable": false,
  "confidence": 0.0,
  "queryRewrite": "火星充电优惠",
  "knowledgeVersion": "kb_2026_07_23_1000",
  "items": [],
  "fallback": {
    "reason": "no_relevant_knowledge",
    "suggestedAction": "clarify_or_handoff"
  },
  "latencyMs": 92
}
```

低置信度：

```json
{
  "requestId": "request_202607230003",
  "traceId": "trace_202607230003",
  "status": "low_confidence",
  "answerable": false,
  "confidence": 0.58,
  "queryRewrite": "卡券是否可以叠加使用",
  "knowledgeVersion": "kb_2026_07_23_1000",
  "items": [],
  "fallback": {
    "reason": "retrieval_confidence_below_threshold",
    "suggestedAction": "answer_carefully_or_handoff"
  },
  "latencyMs": 141
}
```

`not_found` 和 `low_confidence` 会进入知识缺口记录，用于后续提醒业务补充或优化知识。

## 6. Error Response

```json
{
  "requestId": "request_202607230004",
  "traceId": "trace_202607230004",
  "status": "error",
  "answerable": false,
  "confidence": 0.0,
  "queryRewrite": null,
  "knowledgeVersion": null,
  "items": [],
  "error": {
    "code": "rag_qdrant_unavailable",
    "message": "RAG dependency unavailable",
    "retryable": true
  },
  "fallback": {
    "reason": "rag_unavailable",
    "suggestedAction": "safe_fallback"
  },
  "latencyMs": 3000
}
```

错误码：

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

## 7. 状态和阈值

| 状态 | 条件 | Agent 行为 |
| --- | --- | --- |
| `success` | `confidence >= 0.75` 且 `answerable=true` | 基于 `allowedClaims` 回复 |
| `low_confidence` | `0.50 <= confidence < 0.75` | 按知识风险谨慎回答、澄清或转人工 |
| `not_found` | `confidence < 0.50` 或无候选 | 不编造，澄清或转人工 |
| `error` | RAG 或依赖异常 | 安全兜底 |

后续预留按 `knowledgeType` 配置不同阈值。

## 8. Query Rewrite 边界

- Agent 负责意图识别、子意图、槽位、页面上下文和风险等级判断。
- RAG 负责 `queryRewrite`、召回、重排和置信度判断。
- Agent 可以传 `normalizedQueryHint`，例如 `卡券无法使用原因`，但它只是 hint。
- RAG 返回的 `queryRewrite` 只用于观测和审计，Agent 不应把它当成业务结论。
- 第一版 RAG 使用确定性规则改写；后续可在不改接口的情况下切换到小 LLM 改写。

## 9. Agent 使用规则

- Reply Agent 优先基于 `allowedClaims` 组织回复。
- `content` 是知识正文参考，不是最终对客答案。
- 高风险知识必须参考 `forbiddenClaims`。
- RAG 不返回订单金额、余额、退款进度、设备实时状态等业务真值。
- `cards` 第一版保留字段，默认空数组，由 Agent/MCP adapter 决定是否展示。


## 10. 联调资料

Agent 侧调用时机、filters 推荐组合、返回结果消费规则见：

```text
docs/agent_integration_contract_v0.1.md
```

联调样例数据见：

```text
eval/agent_cases.jsonl
```

# 大力仔 Agent 调用 RAG 接口协议 v0.1

## 1. 文档目标

本文只定义 `dalizai-agent-service` 调用独立 RAG 服务时需要的接口格式，包括：

- Agent 什么时候调用 RAG；
- Agent 发给 RAG 的请求字段；
- RAG 返回给 Agent 的响应字段；
- Agent 如何把 RAG 响应转换成内部 `ToolResult`；
- 异常、未命中、低置信度时的统一返回格式。

本文不设计 RAG 内部怎么维护知识库、怎么切片、怎么建索引、怎么训练或怎么做后台运营。这些属于独立 RAG 项目的内部设计。

## 2. 调用位置

在主 Agent 项目中，RAG 应作为一个只读 MCP/Tool 被调用。

推荐保留现有工具名：

```text
faq_knowledge_mcp
```

后续实现方式：

```text
Agno RoutePlanAgent
  -> 判断用户问题属于 FAQ / 规则说明 / 操作指引 / 知识咨询
  -> Executor 调用 faq_knowledge_mcp
  -> faq_knowledge_mcp 通过 HTTP 调用独立 RAG 服务
  -> RAG 返回结构化知识结果
  -> Reply Agent 基于 ToolResult 生成对客回复
```

RAG 不应该被主 Agent 的其他模块到处直接调用，统一从 `faq_knowledge_mcp` 进入。

## 3. Agent 调用 RAG 的接口

### 3.1 HTTP 接口

```http
POST /v1/rag/query
Content-Type: application/json
Authorization: Bearer ${RAG_SERVICE_API_KEY}
```

建议环境变量：

```text
RAG_SERVICE_ENABLED=false
RAG_SERVICE_BASE_URL=http://127.0.0.1:8100
RAG_SERVICE_API_KEY=CHANGE_ME_RAG_SERVICE_API_KEY
RAG_SERVICE_TIMEOUT_MS=3000
RAG_SERVICE_TOP_K=5
```

## 4. 请求格式

### 4.1 Request JSON

```json
{
  "requestId": "request_202607220001",
  "traceId": "trace_202607220001",
  "sessionId": "session_001",
  "userId": "user_001",
  "channel": "wechat_mini_program",
  "query": "怎么扫码充电？",
  "intent": "faq",
  "subIntent": "charge_scan_guide",
  "topK": 5,
  "filters": {
    "knowledgeTypes": ["faq", "operation_guide", "policy"],
    "effectiveOnly": true
  },
  "context": {
    "userProfile": {
      "carBrand": "特斯拉",
      "communicationStyle": "concise"
    },
    "slots": {
      "stationId": null,
      "deviceId": null
    }
  }
}
```

### 4.2 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `requestId` | string | 是 | Agent 当前请求 ID，用于排查问题 |
| `traceId` | string | 是 | 全链路 Trace ID，用于串联 Agent、MCP、RAG 日志 |
| `sessionId` | string | 是 | 当前会话 ID |
| `userId` | string | 否 | 小程序终端用户 ID；RAG 可用于日志记录，不应依赖它做业务判断 |
| `channel` | string | 是 | 渠道，第一版固定 `wechat_mini_program` 即可 |
| `query` | string | 是 | 用户原始问题，或 Agent 改写后的检索问题 |
| `intent` | string | 否 | Agent 识别出的主意图 |
| `subIntent` | string | 否 | Agent 识别出的子意图 |
| `topK` | integer | 否 | 返回候选知识条数，默认 5 |
| `filters` | object | 否 | 检索过滤条件 |
| `context` | object | 否 | 可选上下文，只传低风险、脱敏后的信息 |

### 4.3 filters 字段

```json
{
  "knowledgeTypes": ["faq", "operation_guide", "policy"],
  "effectiveOnly": true,
  "cityCode": "optional",
  "stationId": "optional"
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `knowledgeTypes` | string[] | 限定知识类型，例如 FAQ、操作指引、规则政策 |
| `effectiveOnly` | boolean | 是否只返回当前生效知识，默认 true |
| `cityCode` | string | 可选，城市维度过滤 |
| `stationId` | string | 可选，站点维度过滤 |

第一版可以只实现 `knowledgeTypes` 和 `effectiveOnly`。

## 5. 返回格式

### 5.1 命中知识时

```json
{
  "requestId": "request_202607220001",
  "traceId": "trace_202607220001",
  "status": "success",
  "answerable": true,
  "confidence": 0.86,
  "queryRewrite": "扫码充电操作步骤",
  "knowledgeVersion": "kb_2026_07_22_v1",
  "items": [
    {
      "knowledgeId": "faq_charge_scan_001",
      "chunkId": "chunk_001",
      "title": "扫码充电操作流程",
      "knowledgeType": "operation_guide",
      "summary": "连接充电枪后，通过小程序扫码启动充电。",
      "content": "用户连接充电枪后，可在小程序首页点击扫码充电，扫描设备二维码并确认启动。",
      "score": 0.91,
      "allowedClaims": [
        "用户连接充电枪后，可以在小程序中扫码启动充电。",
        "余额不足或设备不可用时，系统会在启动前提示。"
      ],
      "forbiddenClaims": [
        "一定可以启动成功",
        "可以绕过余额校验启动"
      ],
      "source": {
        "docId": "doc_charge_guide_v3",
        "docTitle": "大力仔小程序充电操作指南",
        "section": "扫码启动充电",
        "updatedAt": "2026-07-20T10:00:00+08:00"
      },
      "cards": [
        {
          "type": "operation_card",
          "title": "去扫码充电",
          "actionType": "route",
          "actionValue": "miniapp_charge_scan"
        }
      ]
    }
  ],
  "latencyMs": 128
}
```

### 5.2 未命中知识时

```json
{
  "requestId": "request_202607220002",
  "traceId": "trace_202607220002",
  "status": "not_found",
  "answerable": false,
  "confidence": 0.0,
  "queryRewrite": "未知问题",
  "knowledgeVersion": "kb_2026_07_22_v1",
  "items": [],
  "fallback": {
    "reason": "no_relevant_knowledge",
    "suggestedAction": "clarify_or_handoff"
  },
  "latencyMs": 92
}
```

### 5.3 低置信度时

```json
{
  "requestId": "request_202607220003",
  "traceId": "trace_202607220003",
  "status": "low_confidence",
  "answerable": false,
  "confidence": 0.58,
  "queryRewrite": "活动券是否可以叠加使用",
  "knowledgeVersion": "kb_2026_07_22_v1",
  "items": [
    {
      "knowledgeId": "policy_coupon_001",
      "chunkId": "chunk_003",
      "title": "卡券使用规则",
      "knowledgeType": "policy",
      "summary": "部分卡券不可叠加使用，具体以活动页展示为准。",
      "content": "部分卡券不可叠加使用，具体以活动页面和订单结算页展示为准。",
      "score": 0.58,
      "allowedClaims": [
        "部分卡券不可叠加使用，具体以活动页面和订单结算页展示为准。"
      ],
      "forbiddenClaims": [
        "所有卡券都可以叠加",
        "一定可以叠加使用"
      ],
      "source": {
        "docId": "policy_coupon_v1",
        "docTitle": "卡券使用规则",
        "section": "叠加规则",
        "updatedAt": "2026-07-20T10:00:00+08:00"
      },
      "cards": []
    }
  ],
  "fallback": {
    "reason": "retrieval_confidence_below_threshold",
    "suggestedAction": "answer_carefully_or_handoff"
  },
  "latencyMs": 141
}
```

### 5.4 RAG 服务异常时

HTTP 非 2xx 或 RAG 内部异常时，建议主 Agent 的 MCP adapter 统一转成如下结构，不把内部错误暴露给用户：

```json
{
  "requestId": "request_202607220004",
  "traceId": "trace_202607220004",
  "status": "error",
  "answerable": false,
  "confidence": 0.0,
  "queryRewrite": null,
  "knowledgeVersion": null,
  "items": [],
  "error": {
    "code": "rag_service_timeout",
    "message": "RAG service timeout",
    "retryable": true
  },
  "fallback": {
    "reason": "rag_unavailable",
    "suggestedAction": "safe_fallback"
  },
  "latencyMs": 3000
}
```

## 6. 返回字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `requestId` | string | 是 | 原样返回 Agent 请求 ID |
| `traceId` | string | 是 | 原样返回 Trace ID |
| `status` | string | 是 | `success` / `not_found` / `low_confidence` / `error` |
| `answerable` | boolean | 是 | RAG 是否认为可以基于命中知识回答 |
| `confidence` | number | 是 | 整体置信度，0 到 1 |
| `queryRewrite` | string/null | 否 | RAG 使用的检索改写问题 |
| `knowledgeVersion` | string/null | 否 | 知识库版本，用于审计追溯 |
| `items` | array | 是 | 命中的知识片段列表 |
| `fallback` | object | 否 | 未命中、低置信度、异常时的建议动作 |
| `error` | object | 否 | 仅异常时返回，Agent 不直接展示给用户 |
| `latencyMs` | integer | 否 | RAG 服务耗时 |

## 7. items 字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `knowledgeId` | string | 是 | 知识 ID，审计和追溯使用 |
| `chunkId` | string | 是 | 知识片段 ID |
| `title` | string | 是 | 知识标题 |
| `knowledgeType` | string | 是 | `faq` / `operation_guide` / `policy` / `troubleshooting` 等 |
| `summary` | string | 是 | 给 Agent 快速理解的摘要 |
| `content` | string | 是 | 可用于生成回复的知识正文，第一版可短一些 |
| `score` | number | 是 | 当前片段相关性得分 |
| `allowedClaims` | string[] | 是 | 允许 Reply Agent 对客表达的信息点 |
| `forbiddenClaims` | string[] | 否 | 禁止 Reply Agent 生成的表述 |
| `source` | object | 是 | 知识来源信息 |
| `cards` | array | 否 | 可选前端卡片或按钮建议 |

## 8. source 字段说明

```json
{
  "docId": "doc_charge_guide_v3",
  "docTitle": "大力仔小程序充电操作指南",
  "section": "扫码启动充电",
  "updatedAt": "2026-07-20T10:00:00+08:00"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `docId` | string | 是 | 来源文档 ID |
| `docTitle` | string | 是 | 来源文档标题 |
| `section` | string | 否 | 来源章节 |
| `updatedAt` | string | 否 | 来源知识更新时间 |

## 9. Agent 内部 ToolResult 映射

RAG 响应进入主 Agent 后，需要由 `faq_knowledge_mcp` 转换为统一工具结果。

### 9.1 成功命中时

```json
{
  "toolCallId": "tool_call_xxx",
  "toolCode": "faq_knowledge_mcp",
  "status": "success",
  "errorCode": null,
  "retryable": false,
  "facts": {
    "answerable": true,
    "confidence": 0.86,
    "queryRewrite": "扫码充电操作步骤",
    "knowledgeVersion": "kb_2026_07_22_v1",
    "items": [
      {
        "knowledgeId": "faq_charge_scan_001",
        "title": "扫码充电操作流程",
        "summary": "连接充电枪后，通过小程序扫码启动充电。",
        "score": 0.91
      }
    ]
  },
  "userVisibleClaims": [
    "用户连接充电枪后，可以在小程序中扫码启动充电。",
    "余额不足或设备不可用时，系统会在启动前提示。"
  ],
  "internalMeta": {
    "ragStatus": "success",
    "latencyMs": 128,
    "sourceKnowledgeIds": ["faq_charge_scan_001"],
    "forbiddenClaims": [
      "一定可以启动成功",
      "可以绕过余额校验启动"
    ]
  },
  "nextAction": "reply_with_knowledge"
}
```

### 9.2 未命中或低置信度时

```json
{
  "toolCallId": "tool_call_xxx",
  "toolCode": "faq_knowledge_mcp",
  "status": "not_found",
  "errorCode": null,
  "retryable": false,
  "facts": {
    "answerable": false,
    "confidence": 0.0,
    "items": []
  },
  "userVisibleClaims": [],
  "internalMeta": {
    "ragStatus": "not_found",
    "fallbackReason": "no_relevant_knowledge",
    "suggestedAction": "clarify_or_handoff"
  },
  "nextAction": "clarify_or_handoff"
}
```

### 9.3 RAG 异常时

```json
{
  "toolCallId": "tool_call_xxx",
  "toolCode": "faq_knowledge_mcp",
  "status": "error",
  "errorCode": "rag_service_timeout",
  "retryable": true,
  "facts": {
    "answerable": false,
    "items": []
  },
  "userVisibleClaims": [],
  "internalMeta": {
    "ragStatus": "error",
    "latencyMs": 3000
  },
  "nextAction": "safe_fallback"
}
```

## 10. Agent 使用规则

Agent 收到 RAG 返回后，按以下规则处理：

| RAG 状态 | Agent 行为 |
| --- | --- |
| `success` 且 `answerable=true` | 使用 `allowedClaims` 生成回复 |
| `low_confidence` | 可以谨慎回答，但不能说确定结论；必要时澄清或人工 |
| `not_found` | 不编造知识，走澄清、通用引导或人工入口 |
| `error` | 不暴露内部错误，走安全兜底 |

强约束：

- Reply Agent 只能使用 `allowedClaims` 和必要的 `summary/content` 组织语言；
- 高风险政策类知识必须检查 `forbiddenClaims`；
- RAG 返回的 `content` 不是最终答案；
- RAG 不返回订单状态、账户余额、退款进度等实时业务真值；
- 需要业务真值时，Agent 应调用订单、账户、退款、充电平台等业务 MCP。

## 11. 最小测试样例

### 11.1 扫码充电 FAQ

用户输入：

```text
怎么扫码充电？
```

预期调用：

```text
Skill: faq_answer
MCP: faq_knowledge_mcp
RAG: POST /v1/rag/query
```

RAG 预期返回：

```json
{
  "status": "success",
  "answerable": true,
  "confidence": 0.8,
  "items": [
    {
      "knowledgeId": "faq_charge_scan_001",
      "allowedClaims": [
        "用户连接充电枪后，可以在小程序中扫码启动充电。"
      ]
    }
  ]
}
```

### 11.2 业务真值问题不由 RAG 回答

用户输入：

```text
我这笔订单为什么扣了 20 块？
```

预期调用：

```text
Skill: order_query
MCP: order_query_mcp
RAG: 不调用，或仅在解释计费规则时辅助调用
```

### 11.3 未命中问题

用户输入：

```text
你们有没有火星充电优惠？
```

RAG 预期返回：

```json
{
  "status": "not_found",
  "answerable": false,
  "confidence": 0,
  "items": []
}
```

Agent 预期行为：不编造活动，澄清或转人工。

## 12. 第一版接口结论

第一版只需要把一个接口打通：

```http
POST /v1/rag/query
```

主 Agent 最关心的返回字段是：

```text
status
answerable
confidence
items[].knowledgeId
items[].summary
items[].content
items[].allowedClaims
items[].forbiddenClaims
items[].source
latencyMs
```

只要这些字段稳定，RAG 项目内部怎么维护知识库、用什么向量库、怎么切片，都可以独立迭代，不影响主 Agent 框架。

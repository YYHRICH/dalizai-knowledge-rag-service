# Agent 对接 RAG 契约指南 v0.1

## 1. 对接目标

本文面向 `dalizai-agent-service` 和 `faq_knowledge_mcp` 的开发同事，说明主 Agent 什么时候调用独立知识 RAG、如何组装请求、如何消费返回结果。

RAG 的边界非常明确：只返回知识依据、允许表达、禁止表达和置信度，不生成最终对客回复。

```text
User -> Agent -> faq_knowledge_mcp -> RAG /v1/rag/query -> Agent Reply
```

## 2. 什么时候调用 RAG

应该调用 RAG 的问题：

- FAQ：扫码充电、结束充电、订单入口、登录问题。
- 操作指引：发票开具、手机号更换、预约说明。
- 规则说明：卡券使用、退款到账规则、停车费规则、计费规则。
- 故障排查：二维码无法识别、枪拔不下来、站点找不到。
- 风险和转人工：赔偿承诺、投诉、无法回答时的处理规则。

不应该直接由 RAG 回答的问题：

- 订单金额、订单状态、支付流水。
- 账户余额、账户实名状态。
- 退款进度、退款金额。
- 设备实时可用状态、充电桩在线状态。
- 任何需要业务数据库实时查询才能确认的事实。

这些问题应优先调用业务 MCP。RAG 最多在业务 MCP 返回后辅助解释一般规则。

## 3. Agent 路由决策建议

建议 Agent 侧先做工具路由：

```text
if query asks real-time business truth:
    call business MCP
elif query asks knowledge, rule, guide, FAQ, troubleshooting, handoff:
    call faq_knowledge_mcp -> RAG
else:
    clarify or safe fallback
```

典型业务真值关键词：

```text
我的订单、这笔订单、订单状态、扣了多少、余额多少、退款到哪了、流水、这个桩现在能不能用
```

典型知识类关键词：

```text
怎么、为什么、规则、流程、入口、能不能、怎么办、说明、多久到账、如何处理
```

注意：关键词只能辅助，不要替代 intent 判断。例如“为什么这单扣了我这么多钱”虽然有“为什么”，但包含“这单”，应优先业务 MCP。

## 4. 请求组装规则

接口：

```http
POST /v1/rag/query
Authorization: Bearer ${RAG_SERVICE_API_KEY}
Content-Type: application/json
```

建议 Agent 请求字段：

```json
{
  "requestId": "request_202607230001",
  "traceId": "trace_202607230001",
  "sessionId": "session_001",
  "userId": "user_001",
  "channel": "wechat_mini_program",
  "originalQuery": "我不会扫码充电，扫哪里啊？",
  "query": "扫码充电操作步骤",
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

字段建议：

- `requestId`: Agent 本次工具调用 ID，必须唯一。
- `traceId`: 用户请求全链路 trace ID，便于排查。
- `sessionId/userId`: 可以传，RAG 只 hash 入库。
- `originalQuery`: 用户原话，便于审计和知识缺口分析。
- `query`: Agent 改写后的检索 query；如果不改写，等于原话。
- `filters`: 推荐传业务域和知识类型，避免跨域误召回。
- `context`: 只传脱敏、低风险上下文；不要传订单明细、余额、手机号、身份证等敏感或实时业务真值。

## 5. 推荐 filters 组合

| 场景 | businessDomains | knowledgeTypes |
| --- | --- | --- |
| 扫码/启动/结束充电 | `charging` | `faq`, `operation_guide` |
| 设备二维码/枪线/设备异常 | `device` | `troubleshooting`, `faq` |
| 站点、停车、导航 | `station` | `service_rule`, `faq` |
| 费用规则、扣费规则说明 | `payment` | `billing_policy`, `faq` |
| 卡券、优惠券、活动规则 | `coupon` | `coupon_policy`, `faq` |
| 退款规则，不查进度 | `refund` | `refund_policy`, `faq` |
| 发票开具流程 | `invoice` | `operation_guide`, `faq` |
| 登录、账户、手机号更换 | `account` | `faq`, `operation_guide` |
| 订单入口、订单展示说明 | `order` | `faq`, `operation_guide` |
| 投诉、赔偿、转人工 | `customer_service` | `handoff_guide`, `risk_notice` |

第一版不强制限制组合，但建议按上表传，减少噪声。

## 6. Response 消费规则

### success

Agent 可以基于 `items[0..n].allowedClaims` 组织回复。

必须遵守：

- 优先使用 `allowedClaims`，`content` 只作上下文参考。
- 不得输出 `forbiddenClaims` 中禁止的承诺或判断。
- 高风险知识必须显式检查 `forbiddenClaims`。
- 不要把 `confidence`、`knowledgeId`、`chunkId` 暴露给用户。

### low_confidence

Agent 不应直接当作确定答案。

建议动作：

- 问法模糊：追问澄清。
- 风险较低且命中知识明显：谨慎回答，并避免绝对化。
- 风险较高：转人工或调用业务 MCP。

### not_found

Agent 不允许编造。

建议动作：

- 追问澄清。
- 转人工。
- 如果是业务真值问题，改调业务 MCP。

`not_found` 会进入知识缺口，后续由业务补知识。

### error

RAG 依赖异常或服务异常。

建议动作：

- 使用安全兜底话术。
- 可按 `error.retryable=true` 做一次短重试。
- 不要因为 RAG error 编造答案。

## 7. Agent 回复组装伪代码

```python
def handle_rag_result(rag_result):
    if rag_result["status"] == "success" and rag_result["answerable"]:
        claims = []
        forbidden = []
        for item in rag_result["items"]:
            claims.extend(item["allowedClaims"])
            forbidden.extend(item.get("forbiddenClaims", []))
        return reply_with_claims(claims, forbidden)

    if rag_result["status"] == "low_confidence":
        return clarify_or_handoff(rag_result["fallback"])

    if rag_result["status"] == "not_found":
        return clarify_or_handoff(rag_result["fallback"])

    if rag_result["status"] == "error":
        return safe_fallback()
```

## 8. Curl 示例

```powershell
$body = @{
  requestId = "request_demo_001"
  traceId = "trace_demo_001"
  sessionId = "session_demo_001"
  channel = "wechat_mini_program"
  originalQuery = "第一次用这个桩怎么开始？"
  query = "第一次用这个桩怎么开始？"
  intent = "faq"
  subIntent = "charge_scan_guide"
  topK = 5
  filters = @{
    businessDomains = @("charging")
    knowledgeTypes = @("faq", "operation_guide")
    effectiveOnly = $true
    cityCode = $null
    stationId = $null
  }
  context = @{}
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8100/v1/rag/query" `
  -Headers @{ Authorization = "Bearer $env:RAG_SERVICE_API_KEY" } `
  -ContentType "application/json" `
  -Body $body
```

## 9. Python 调用示例

```python
import httpx

payload = {
    "requestId": "request_demo_001",
    "traceId": "trace_demo_001",
    "sessionId": "session_demo_001",
    "channel": "wechat_mini_program",
    "originalQuery": "优惠券能不能叠加？",
    "query": "卡券是否可以叠加使用",
    "intent": "faq",
    "subIntent": "coupon_stack_rule",
    "filters": {
        "businessDomains": ["coupon"],
        "knowledgeTypes": ["coupon_policy", "faq"],
        "effectiveOnly": True,
    },
}

response = httpx.post(
    "http://127.0.0.1:8100/v1/rag/query",
    headers={"Authorization": f"Bearer {RAG_SERVICE_API_KEY}"},
    json=payload,
    timeout=3.0,
)
response.raise_for_status()
rag_result = response.json()
```

## 10. 联调验收标准

第一轮 Agent-RAG 联调建议通过以下验收：

- Agent 能正确区分 RAG 与业务 MCP，业务真值问题不直接走 RAG。
- `success` 时 Agent 只基于 `allowedClaims/content` 回复。
- `forbiddenClaims` 不被输出或反向承诺。
- `low_confidence/not_found/error` 不编造，能澄清、转人工或安全兜底。
- `requestId/traceId/sessionId/channel/filters` 能稳定透传。
- RAG audit log 可以用 `traceId` 回查。
- `eval/agent_cases.jsonl` 样例能作为联调基准。


## 11. 调试台

开发联调时可以打开：

```text
http://127.0.0.1:8100/debug
```

页面支持手动输入 query、选择 eval case、查看召回知识、allowedClaims、forbiddenClaims、status、confidence 和评测对比。

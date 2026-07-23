# Agent-RAG 联调模拟数据集需求 v0.1

## 1. 目标

请 Agent 开发同事协助生成一份模拟数据集，用于独立知识 RAG 服务和主 Agent 的联调、评测与回归测试。

这份数据集主要回答三个问题：

1. Agent 在什么情况下应该调用 RAG。
2. Agent 调 RAG 时会传什么 query、intent、filters。
3. RAG 应该返回什么状态和命中哪条知识。

RAG 服务只负责 FAQ、操作指引、规则说明、故障排查、转人工指引等知识类问题。订单金额、账户余额、退款进度、设备实时状态等业务真值问题应优先走业务 MCP，RAG 最多辅助解释规则。

## 2. 交付格式

优先提供 JSONL 文件，每行一个 case。

建议文件名：

```text
agent_rag_cases.jsonl
```

如果暂时不方便给 JSONL，也可以先给 Excel，字段按本文第 3 节提供即可。

## 3. 字段要求

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 用例 ID，例如 `case_001` |
| `originalQuery` | string | 是 | 用户原始问题 |
| `query` | string | 是 | Agent 准备传给 RAG 的检索 query；如果不改写，则等于原始问题 |
| `intent` | string/null | 否 | Agent 识别出的主意图 |
| `subIntent` | string/null | 否 | Agent 识别出的子意图 |
| `channel` | string | 是 | 第一版默认 `wechat_mini_program` |
| `filters` | object | 是 | Agent 计划传给 RAG 的过滤条件 |
| `shouldCallRag` | boolean | 是 | 该问题是否应该调用 RAG |
| `primaryTool` | string | 是 | Agent 首选工具，例如 `faq_knowledge_mcp`、`order_query_mcp` |
| `expectedStatus` | string | 是 | 预期 RAG 状态：`success` / `low_confidence` / `not_found` / `not_called` |
| `expectedKnowledgeId` | string/null | 否 | 预期命中的知识 ID；不确定或不应命中则为 null |
| `expectedNextAction` | string | 是 | Agent 后续动作建议 |
| `riskLevel` | string | 否 | `low` / `medium` / `high` / `critical` |
| `notes` | string | 否 | 补充说明 |

`filters` 示例：

```json
{
  "businessDomains": ["charging"],
  "knowledgeTypes": ["faq", "operation_guide"],
  "effectiveOnly": true,
  "cityCode": null,
  "stationId": null
}
```

## 4. 业务域枚举

第一版请优先使用以下 `businessDomains`：

```text
charging            充电流程与充电行为
device              充电设备、枪线、二维码、设备异常
station             站点、停车、导航、场站规则
payment             支付、扣费、余额、账单说明
coupon              卡券、优惠券、活动优惠
refund              退款规则、退款说明
invoice             发票
account             登录、账户、手机号、个人信息
order               订单说明、订单展示、订单入口
customer_service    人工客服、转人工规则、投诉入口
general             通用说明
```

## 5. 知识类型枚举

第一版请优先使用以下 `knowledgeTypes`：

```text
faq                 常见问答
operation_guide     操作指引
billing_policy      计费/扣费规则
coupon_policy       卡券/活动/优惠规则
refund_policy       退款规则
troubleshooting     故障排查
handoff_guide       转人工指引
service_rule        平台服务规则、使用规则
risk_notice         风险提示、禁止承诺、免责声明
```

## 6. expectedNextAction 建议枚举

```text
reply_with_knowledge        基于 RAG 知识回复
answer_carefully            谨慎回答
clarify                     追问澄清
handoff                     转人工
safe_fallback               安全兜底
call_business_mcp           调业务 MCP
not_call_rag                不调用 RAG
```

## 7. 必须覆盖的场景

请尽量提供 50-100 条模拟数据。第一批至少覆盖以下场景，每类建议 3-10 条。

### 7.1 应该调用 RAG，且预期 success

- 扫码充电操作
- 结束充电操作
- 卡券是否可用、是否叠加
- 退款规则说明
- 发票开具流程
- 账户登录/手机号更换说明
- 停车费/站点规则说明
- 常见设备故障排查
- 转人工入口或规则

### 7.2 应该调用 RAG，但可能 low_confidence

- 问法模糊的问题
- 同时涉及多个规则的问题
- 用户表达不完整的问题
- 类似政策但缺少关键上下文的问题

### 7.3 应该调用 RAG，但预期 not_found

- 不存在的优惠活动
- 知识库暂未覆盖的新问题
- 超出业务范围的奇怪问题
- 未发布政策或未生效活动

### 7.4 不应该直接由 RAG 回答

这些 case 的 `shouldCallRag=false`，`expectedStatus=not_called`。

- 我的订单为什么扣了 20 块？
- 我的退款到哪了？
- 我的账户余额是多少？
- 这个充电桩现在能不能用？
- 我的订单现在是什么状态？
- 能不能赔我多少钱？
- 帮我查一下支付流水。

这些问题应优先调用业务 MCP，RAG 最多在业务 MCP 返回后辅助解释规则。

## 8. JSONL 示例

```jsonl
{"id":"case_001","originalQuery":"我不会扫码充电，扫哪里啊？","query":"扫码充电操作步骤","intent":"faq","subIntent":"charge_scan_guide","channel":"wechat_mini_program","filters":{"businessDomains":["charging"],"knowledgeTypes":["faq","operation_guide"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"faq_charge_scan_001","expectedNextAction":"reply_with_knowledge","riskLevel":"low","notes":"普通充电 FAQ"}
{"id":"case_002","originalQuery":"优惠券能不能叠加？","query":"卡券是否可以叠加使用","intent":"faq","subIntent":"coupon_stack_rule","channel":"wechat_mini_program","filters":{"businessDomains":["coupon"],"knowledgeTypes":["coupon_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"coupon_stack_001","expectedNextAction":"reply_with_knowledge","riskLevel":"high","notes":"高风险政策类，RAG 需返回 forbiddenClaims"}
{"id":"case_003","originalQuery":"我这笔订单为什么扣了20块？","query":"订单扣费原因查询","intent":"order_query","subIntent":"order_deduction_reason","channel":"wechat_mini_program","filters":{"businessDomains":["order","payment"],"knowledgeTypes":["billing_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":false,"primaryTool":"order_query_mcp","expectedStatus":"not_called","expectedKnowledgeId":null,"expectedNextAction":"call_business_mcp","riskLevel":"high","notes":"涉及具体订单真值，不应由 RAG 直接回答"}
{"id":"case_004","originalQuery":"你们有没有火星充电优惠？","query":"火星充电优惠活动","intent":"faq","subIntent":"promotion_query","channel":"wechat_mini_program","filters":{"businessDomains":["coupon"],"knowledgeTypes":["coupon_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"not_found","expectedKnowledgeId":null,"expectedNextAction":"clarify","riskLevel":"medium","notes":"不存在活动，不允许编造"}
```


## 9. 扩展示例

下面这些 case 可以直接作为样例，后续按同样格式扩展到 50-100 条。

```jsonl
{"id":"case_001","originalQuery":"我不会扫码充电，扫哪里啊？","query":"扫码充电操作步骤","intent":"faq","subIntent":"charge_scan_guide","channel":"wechat_mini_program","filters":{"businessDomains":["charging"],"knowledgeTypes":["faq","operation_guide"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"faq_charge_scan_001","expectedNextAction":"reply_with_knowledge","riskLevel":"low","notes":"普通充电 FAQ"}
{"id":"case_002","originalQuery":"怎么结束充电？","query":"结束充电操作步骤","intent":"faq","subIntent":"charge_stop_guide","channel":"wechat_mini_program","filters":{"businessDomains":["charging"],"knowledgeTypes":["faq","operation_guide"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"faq_charge_stop_001","expectedNextAction":"reply_with_knowledge","riskLevel":"low","notes":"普通操作指引"}
{"id":"case_003","originalQuery":"优惠券能不能叠加？","query":"卡券是否可以叠加使用","intent":"faq","subIntent":"coupon_stack_rule","channel":"wechat_mini_program","filters":{"businessDomains":["coupon"],"knowledgeTypes":["coupon_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"coupon_stack_001","expectedNextAction":"reply_with_knowledge","riskLevel":"high","notes":"高风险政策类，需要 forbiddenClaims"}
{"id":"case_004","originalQuery":"退款一般多久到账？","query":"退款到账时间规则","intent":"faq","subIntent":"refund_arrival_rule","channel":"wechat_mini_program","filters":{"businessDomains":["refund"],"knowledgeTypes":["refund_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"refund_arrival_001","expectedNextAction":"reply_with_knowledge","riskLevel":"high","notes":"退款规则说明，不查询具体退款进度"}
{"id":"case_005","originalQuery":"我的退款到哪了？","query":"退款进度查询","intent":"refund_query","subIntent":"refund_status_query","channel":"wechat_mini_program","filters":{"businessDomains":["refund"],"knowledgeTypes":["refund_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":false,"primaryTool":"refund_query_mcp","expectedStatus":"not_called","expectedKnowledgeId":null,"expectedNextAction":"call_business_mcp","riskLevel":"high","notes":"具体退款进度是业务真值，不由 RAG 回答"}
{"id":"case_006","originalQuery":"我这笔订单为什么扣了20块？","query":"订单扣费原因查询","intent":"order_query","subIntent":"order_deduction_reason","channel":"wechat_mini_program","filters":{"businessDomains":["order","payment"],"knowledgeTypes":["billing_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":false,"primaryTool":"order_query_mcp","expectedStatus":"not_called","expectedKnowledgeId":null,"expectedNextAction":"call_business_mcp","riskLevel":"high","notes":"具体订单扣费原因需要订单 MCP"}
{"id":"case_007","originalQuery":"为啥会扣停车费？","query":"停车费规则说明","intent":"faq","subIntent":"station_parking_fee_rule","channel":"wechat_mini_program","filters":{"businessDomains":["station"],"knowledgeTypes":["service_rule","billing_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"rule_station_parking_001","expectedNextAction":"reply_with_knowledge","riskLevel":"medium","notes":"站点规则说明，不涉及具体订单金额"}
{"id":"case_008","originalQuery":"二维码扫不出来怎么办？","query":"充电设备二维码无法识别处理方法","intent":"faq","subIntent":"device_qrcode_scan_failed","channel":"wechat_mini_program","filters":{"businessDomains":["device"],"knowledgeTypes":["troubleshooting","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"trouble_qrcode_scan_001","expectedNextAction":"reply_with_knowledge","riskLevel":"medium","notes":"设备故障排查"}
{"id":"case_009","originalQuery":"这个桩现在能不能用？","query":"充电桩实时可用状态查询","intent":"device_status_query","subIntent":"charger_availability","channel":"wechat_mini_program","filters":{"businessDomains":["device","station"],"knowledgeTypes":["troubleshooting","faq"],"effectiveOnly":true,"cityCode":null,"stationId":"STATION_MOCK_001"},"shouldCallRag":false,"primaryTool":"charging_platform_mcp","expectedStatus":"not_called","expectedKnowledgeId":null,"expectedNextAction":"call_business_mcp","riskLevel":"high","notes":"设备实时状态是业务真值"}
{"id":"case_010","originalQuery":"发票在哪里开？","query":"发票开具入口和流程","intent":"faq","subIntent":"invoice_apply_guide","channel":"wechat_mini_program","filters":{"businessDomains":["invoice"],"knowledgeTypes":["operation_guide","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"guide_invoice_apply_001","expectedNextAction":"reply_with_knowledge","riskLevel":"low","notes":"发票操作指引"}
{"id":"case_011","originalQuery":"能不能赔我点钱？","query":"赔偿承诺处理规则","intent":"complaint","subIntent":"compensation_request","channel":"wechat_mini_program","filters":{"businessDomains":["customer_service"],"knowledgeTypes":["handoff_guide","risk_notice"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"success","expectedKnowledgeId":"handoff_compensation_request_001","expectedNextAction":"handoff","riskLevel":"critical","notes":"不能由 Agent 承诺赔偿，命中转人工/风险提示"}
{"id":"case_012","originalQuery":"你们有没有火星充电优惠？","query":"火星充电优惠活动","intent":"faq","subIntent":"promotion_query","channel":"wechat_mini_program","filters":{"businessDomains":["coupon"],"knowledgeTypes":["coupon_policy","faq"],"effectiveOnly":true,"cityCode":null,"stationId":null},"shouldCallRag":true,"primaryTool":"faq_knowledge_mcp","expectedStatus":"not_found","expectedKnowledgeId":null,"expectedNextAction":"clarify","riskLevel":"medium","notes":"不存在活动，不允许编造"}
```

建议额外补充一些真实口语化变体，例如：

```text
扫哪里啊
二维码没反应
券咋用不了
退款咋还没到
凭啥扣我钱
这个桩坏了吗
我要找人工
```

## 10. 质量要求

- 不要包含真实手机号、车牌号、订单号、身份证号、支付流水号。
- 如需模拟敏感信息，请使用假数据，例如 `13800000000`、`ORDER_MOCK_001`。
- 问法要尽量贴近真实用户表达，可以包含口语、错别字、短句。
- 同一个知识点建议提供多个相似问法，方便评测召回稳定性。
- 对于业务真值问题，请明确 `shouldCallRag=false`，避免 RAG 越权回答。

## 11. 交付后用途

收到数据后，我们会转换为：

```text
eval/agent_cases.jsonl
```

后续用于：

- Agent 路由评测
- RAG 检索评测
- RAG 和业务 MCP 边界验证
- 低置信度和未命中知识缺口分析
- 回归测试

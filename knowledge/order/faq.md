---
docId: doc_order_faq_v1
docTitle: 订单常见问题
businessDomain: order
knowledgeType: faq
riskLevel: medium
status: active
ownerTeam: 客服运营
owner:
effectiveFrom: 2026-07-23T00:00:00+08:00
effectiveTo:
updatedAt: 2026-07-23T00:00:00+08:00
reviewDueAt: 2026-09-21T00:00:00+08:00
channels:
  - wechat_mini_program
cityCodes:
stationIds:
---

# 订单常见问题

## faq_order_where_001｜在哪里查看订单？

### Summary
用户可以在小程序订单入口查看历史订单和当前订单。

### Content
用户可以进入小程序订单入口查看当前订单和历史订单。订单详情通常会展示订单状态、充电时间、费用明细等信息。具体展示字段以小程序页面为准。

### Allowed Claims
- 用户可以在小程序订单入口查看当前订单和历史订单。
- 订单详情通常会展示订单状态、充电时间、费用明细等信息。
- 具体展示字段以小程序页面为准。

### Forbidden Claims
- 可以查看其他用户的订单。
- 未登录也可以查看个人订单。

### Keywords
- 订单
- 历史订单
- 当前订单
- 订单详情

### Similar Questions
- 在哪里看订单？
- 历史订单怎么查？
- 充电订单在哪里？

### Eval Questions
[
  {
    "question": "在哪里查看历史订单？",
    "referenceAnswer": "用户可以在小程序订单入口查看当前订单和历史订单。订单详情通常会展示订单状态、充电时间、费用明细等信息。具体展示字段以小程序页面为准。",
    "expectedContextIds": ["faq_order_where_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "用户可以在小程序订单入口查看当前订单和历史订单。",
      "订单详情通常会展示订单状态、充电时间、费用明细等信息。"
    ],
    "negativeContextIds": [],
    "notes": "订单入口 FAQ。"
  }
]

## faq_order_realtime_001｜订单实时状态能直接从知识库回答吗？

### Summary
订单实时状态属于业务真值，需要通过订单系统查询后确认。

### Content
订单实时状态、订单金额、退款状态等属于业务真值，不能仅凭知识库内容直接回答。用户询问具体订单时，应通过订单系统或相关业务系统查询后确认，再向用户说明。

### Allowed Claims
- 订单实时状态、订单金额、退款状态等属于业务真值，需要通过业务系统查询后确认。
- 知识库不能直接判断某笔订单的实时状态。

### Forbidden Claims
- 未查询订单系统时确认订单状态。
- 根据历史记忆判断实时订单状态。
- 编造订单金额或订单结果。

### Keywords
- 订单状态
- 业务真值
- 实时查询
- 订单系统

### Similar Questions
- 我的订单现在什么状态？
- 这笔订单完成了吗？
- 订单金额对不对？

### Eval Questions
[
  {
    "question": "我的订单现在什么状态？",
    "referenceAnswer": "订单实时状态、订单金额、退款状态等属于业务真值，需要通过业务系统查询后确认。知识库不能直接判断某笔订单的实时状态。",
    "expectedContextIds": ["faq_order_realtime_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "订单实时状态、订单金额、退款状态等属于业务真值，需要通过业务系统查询后确认。",
      "知识库不能直接判断某笔订单的实时状态。"
    ],
    "negativeContextIds": ["faq_order_where_001#main"],
    "notes": "RAG 边界，Agent 应调用订单 MCP。"
  }
]

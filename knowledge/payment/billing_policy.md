---
docId: doc_payment_billing_policy_v1
docTitle: 计费与扣费规则
businessDomain: payment
knowledgeType: billing_policy
riskLevel: high
status: active
ownerTeam: 财务运营
owner:
effectiveFrom: 2026-07-23T00:00:00+08:00
effectiveTo:
updatedAt: 2026-07-23T00:00:00+08:00
reviewDueAt: 2026-08-22T00:00:00+08:00
channels:
  - wechat_mini_program
cityCodes:
stationIds:
---

# 计费与扣费规则

## bill_fee_rule_001｜充电费用怎么计算？

### Summary
充电费用通常由电费、服务费等组成，具体金额以订单结算页和实际订单为准。

### Content
充电费用通常由电费、服务费等组成，不同站点、不同时段的计费规则可能不同。用户在启动充电前可查看页面展示的价格信息；订单结束后，系统会根据实际充电量、站点价格规则和订单情况生成最终费用。

### Allowed Claims
- 充电费用通常由电费、服务费等组成。
- 不同站点、不同时段的计费规则可能不同。
- 最终费用以订单结算页和实际订单为准。

### Forbidden Claims
- 所有站点价格都一样。
- 可以提前承诺最终扣费金额。
- 可以绕过订单计费规则。

### Keywords
- 计费
- 电费
- 服务费
- 扣费规则

### Similar Questions
- 充电费用怎么算？
- 服务费是什么？
- 为什么每个站价格不一样？

### Eval Questions
[
  {
    "question": "充电费用怎么计算？",
    "referenceAnswer": "充电费用通常由电费、服务费等组成，不同站点、不同时段的计费规则可能不同。最终费用以订单结算页和实际订单为准。",
    "expectedContextIds": ["bill_fee_rule_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "充电费用通常由电费、服务费等组成。",
      "不同站点、不同时段的计费规则可能不同。",
      "最终费用以订单结算页和实际订单为准。"
    ],
    "negativeContextIds": [],
    "notes": "计费规则说明，不回答具体订单金额。"
  }
]

## bill_abnormal_deduction_001｜觉得订单扣费异常怎么办？

### Summary
用户认为订单扣费异常时，应通过业务系统查询具体订单后确认。

### Content
如果用户认为某笔订单扣费异常，需要结合具体订单信息、充电量、计费规则和订单状态进行核验。RAG 知识只能说明一般计费规则，不能直接判断某笔订单是否扣费错误。用户可在订单详情页查看费用明细，或联系人工客服协助核验。

### Allowed Claims
- 订单扣费异常需要结合具体订单信息、充电量、计费规则和订单状态核验。
- 一般知识只能说明计费规则，不能直接判断某笔订单是否扣费错误。
- 用户可以在订单详情页查看费用明细，或联系人工客服协助核验。

### Forbidden Claims
- 未查询订单时确认扣费错误。
- 直接承诺退款或赔偿。
- 直接判断某笔订单一定异常。

### Keywords
- 扣费异常
- 费用明细
- 订单金额
- 多扣费

### Similar Questions
- 为什么这单扣这么多？
- 我是不是被多扣了？
- 这笔订单费用不对怎么办？

### Eval Questions
[
  {
    "question": "为什么这单扣了我这么多钱？",
    "referenceAnswer": "订单扣费异常需要结合具体订单信息、充电量、计费规则和订单状态核验。一般知识只能说明计费规则，不能直接判断某笔订单是否扣费错误。用户可以在订单详情页查看费用明细，或联系人工客服协助核验。",
    "expectedContextIds": ["bill_abnormal_deduction_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "订单扣费异常需要结合具体订单信息、充电量、计费规则和订单状态核验。",
      "一般知识只能说明计费规则，不能直接判断某笔订单是否扣费错误。"
    ],
    "negativeContextIds": ["refund_arrival_001#main"],
    "notes": "该问题在 Agent 中应优先查订单 MCP，RAG 仅作为规则说明。"
  }
]

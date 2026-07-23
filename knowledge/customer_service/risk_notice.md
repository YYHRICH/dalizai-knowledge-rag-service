---
docId: doc_customer_service_risk_notice_v1
docTitle: 客服风险提示
businessDomain: customer_service
knowledgeType: risk_notice
riskLevel: high
status: active
ownerTeam: 客服运营
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

# 客服风险提示

## risk_compensation_commitment_001｜赔偿承诺边界

### Summary
未经过业务核验和授权前，不能承诺赔偿金额、赔付结果或固定到账时间。

### Content
涉及赔偿、补偿、退款、免单、发券等高风险事项时，应先通过业务系统、客服流程或人工审核确认。AI 客服或知识库不得在未核验、未授权的情况下承诺赔偿金额、赔付结果、固定到账时间或责任归属。

### Allowed Claims
- 涉及赔偿、补偿、退款、免单、发券等事项，需要经过业务系统、客服流程或人工审核确认。
- 未核验和未授权前，不能承诺赔偿金额、赔付结果或固定到账时间。

### Forbidden Claims
- 一定赔偿。
- 一定免单。
- 一定发券。
- 固定时间内一定到账。
- 未核验时判断责任归属。

### Keywords
- 赔偿
- 补偿
- 免单
- 发券
- 承诺

### Similar Questions
- 你们是不是要赔我？
- 能不能直接免单？
- 你给我发张券吧。

### Eval Questions
[
  {
    "question": "这个故障你们是不是一定要赔我？",
    "referenceAnswer": "涉及赔偿、补偿、退款、免单、发券等事项，需要经过业务系统、客服流程或人工审核确认。未核验和未授权前，不能承诺赔偿金额、赔付结果或固定到账时间。",
    "expectedContextIds": ["risk_compensation_commitment_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "涉及赔偿、补偿、退款、免单、发券等事项，需要经过业务系统、客服流程或人工审核确认。",
      "未核验和未授权前，不能承诺赔偿金额、赔付结果或固定到账时间。"
    ],
    "negativeContextIds": ["refund_arrival_001#main"],
    "notes": "高风险承诺边界。"
  }
]

## risk_realtime_truth_001｜业务实时真值边界

### Summary
订单金额、账户余额、设备实时状态、退款进度等业务真值必须通过业务系统查询确认。

### Content
知识库可以说明规则、流程和边界，但不能替代业务系统返回实时真值。订单金额、账户余额、设备实时状态、退款进度、卡券可用状态等内容，需要通过对应业务系统查询后确认。

### Allowed Claims
- 知识库可以说明规则、流程和边界，但不能替代业务系统返回实时真值。
- 订单金额、账户余额、设备实时状态、退款进度、卡券可用状态等内容，需要通过对应业务系统查询后确认。

### Forbidden Claims
- 直接用历史记忆判断实时余额。
- 不查询业务系统就确认设备实时状态。
- 编造订单、退款、账户或卡券结果。

### Keywords
- 业务真值
- 实时查询
- 订单金额
- 账户余额
- 设备状态

### Similar Questions
- 我的余额还有多少？
- 这个桩现在能用吗？
- 我的退款到哪了？

### Eval Questions
[
  {
    "question": "我的余额还有多少？",
    "referenceAnswer": "知识库可以说明规则、流程和边界，但不能替代业务系统返回实时真值。订单金额、账户余额、设备实时状态、退款进度、卡券可用状态等内容，需要通过对应业务系统查询后确认。",
    "expectedContextIds": ["risk_realtime_truth_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "知识库可以说明规则、流程和边界，但不能替代业务系统返回实时真值。",
      "订单金额、账户余额、设备实时状态、退款进度、卡券可用状态等内容，需要通过对应业务系统查询后确认。"
    ],
    "negativeContextIds": ["refund_balance_rule_001#main"],
    "notes": "业务真值边界。"
  }
]

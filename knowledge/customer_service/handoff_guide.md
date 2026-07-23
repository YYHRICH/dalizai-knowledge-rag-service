---
docId: doc_customer_service_handoff_v1
docTitle: 转人工指引
businessDomain: customer_service
knowledgeType: handoff_guide
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

# 转人工指引

## handoff_unanswerable_001｜无法确认的问题如何处理？

### Summary
当问题涉及业务真值、赔偿承诺、法律判断或知识库低置信度时，应引导用户联系人工客服。

### Content
如果用户问题涉及订单金额、退款进度、设备实时状态、赔偿承诺、法律责任判断，或当前知识库无法提供可靠依据，应引导用户联系人工客服进一步确认。转人工时应说明需要结合具体情况处理，不应承诺处理结果。

### Allowed Claims
- 这个问题需要结合具体情况进一步确认，建议联系人工客服处理。
- 涉及订单、退款或设备实时状态的问题，需要通过业务系统查询后确认。
- 转人工不代表已经确认处理结果。

### Forbidden Claims
- 直接承诺赔偿金额。
- 在没有业务系统结果时判断订单、退款或设备实时状态。
- 承诺人工一定会按用户要求处理。

### Keywords
- 转人工
- 人工客服
- 无法确认
- 业务真值

### Similar Questions
- 这个能找人工吗？
- 你们客服在哪里？
- 这个问题你处理不了怎么办？

### Eval Questions
[
  {
    "question": "这个问题你处理不了怎么办？",
    "referenceAnswer": "这个问题需要结合具体情况进一步确认，建议联系人工客服处理。涉及订单、退款或设备实时状态的问题，需要通过业务系统查询后确认。转人工不代表已经确认处理结果。",
    "expectedContextIds": ["handoff_unanswerable_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "这个问题需要结合具体情况进一步确认，建议联系人工客服处理。",
      "涉及订单、退款或设备实时状态的问题，需要通过业务系统查询后确认。"
    ],
    "negativeContextIds": [],
    "notes": "转人工边界。"
  }
]

## handoff_complaint_001｜用户要投诉怎么办？

### Summary
用户表达投诉诉求时，应引导进入投诉或人工客服流程，并保留必要问题描述。

### Content
如果用户明确表达投诉、强烈不满或要求人工处理，应引导其进入投诉或人工客服流程。可提示用户补充订单号、站点、设备、时间和问题描述，以便客服进一步核验。知识库不直接判断投诉结果或责任归属。

### Allowed Claims
- 用户表达投诉诉求时，可以引导进入投诉或人工客服流程。
- 用户可补充订单号、站点、设备、时间和问题描述，便于进一步核验。
- 知识库不直接判断投诉结果或责任归属。

### Forbidden Claims
- 直接判定责任方。
- 承诺投诉一定成立。
- 承诺固定赔偿。

### Keywords
- 投诉
- 不满意
- 人工处理
- 责任

### Similar Questions
- 我要投诉。
- 这事必须给我处理。
- 我要找人工客服。

### Eval Questions
[
  {
    "question": "我要投诉你们这个站点。",
    "referenceAnswer": "用户表达投诉诉求时，可以引导进入投诉或人工客服流程。用户可补充订单号、站点、设备、时间和问题描述，便于进一步核验。知识库不直接判断投诉结果或责任归属。",
    "expectedContextIds": ["handoff_complaint_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "用户表达投诉诉求时，可以引导进入投诉或人工客服流程。",
      "知识库不直接判断投诉结果或责任归属。"
    ],
    "negativeContextIds": ["risk_compensation_commitment_001#main"],
    "notes": "投诉入口。"
  }
]

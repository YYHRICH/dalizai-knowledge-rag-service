---
docId: doc_refund_policy_v1
docTitle: 退款规则说明
businessDomain: refund
knowledgeType: refund_policy
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

# 退款规则说明

## refund_arrival_001｜退款一般多久到账？

### Summary
退款到账时间受支付渠道和银行处理时效影响，具体进度需以业务系统查询结果为准。

### Content
退款申请提交后，到账时间会受支付渠道、银行或第三方支付机构处理时效影响。用户如需确认某笔退款的实时进度，应通过业务系统查询后确认。知识库只能提供一般规则说明，不能确认某笔退款已经到账。

### Allowed Claims
- 退款到账时间会受支付渠道、银行或第三方支付机构处理时效影响。
- 某笔退款的实时进度需要通过业务系统查询后确认。
- 知识库只能提供一般规则说明，不能确认某笔退款已经到账。

### Forbidden Claims
- 一定会在固定时间到账。
- 在未查询业务系统时确认某笔退款已经到账。
- 承诺额外赔偿。

### Keywords
- 退款
- 到账
- 退款时间
- 退款进度

### Similar Questions
- 退款多久到？
- 钱什么时候退回来？
- 退款怎么还没到？

### Eval Questions
[
  {
    "question": "退款一般多久到账？",
    "referenceAnswer": "退款到账时间会受支付渠道、银行或第三方支付机构处理时效影响。某笔退款的实时进度需要通过业务系统查询后确认。知识库只能提供一般规则说明，不能确认某笔退款已经到账。",
    "expectedContextIds": ["refund_arrival_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "退款到账时间会受支付渠道、银行或第三方支付机构处理时效影响。",
      "某笔退款的实时进度需要通过业务系统查询后确认。"
    ],
    "negativeContextIds": [],
    "notes": "规则说明，不回答具体退款进度。"
  }
]

## refund_balance_rule_001｜余额可以提现吗？

### Summary
余额退款或提现需满足平台规则，具体可退金额和进度应以账户与退款系统查询结果为准。

### Content
用户如需申请余额退款或提现，需要满足平台当前规则和账户状态要求。具体可退金额、是否存在赠送金影响、是否有未完结订单、是否已有退款申请，需要通过账户与退款系统查询后确认。知识库不能直接判断用户个人账户能退多少钱。

### Allowed Claims
- 余额退款或提现需满足平台当前规则和账户状态要求。
- 具体可退金额、赠送金影响、未完结订单和申请状态需要通过业务系统查询后确认。
- 知识库不能直接判断用户个人账户能退多少钱。

### Forbidden Claims
- 未查询账户时承诺具体可退金额。
- 承诺一定能提现成功。
- 忽略赠送金、未完结订单或账户状态限制。

### Keywords
- 余额
- 提现
- 退款
- 可退金额

### Similar Questions
- 余额可以提现吗？
- 账户里的钱能退吗？
- 我的余额可以退多少？

### Eval Questions
[
  {
    "question": "我的余额可以退多少？",
    "referenceAnswer": "余额退款或提现需满足平台当前规则和账户状态要求。具体可退金额、赠送金影响、未完结订单和申请状态需要通过业务系统查询后确认。知识库不能直接判断用户个人账户能退多少钱。",
    "expectedContextIds": ["refund_balance_rule_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "余额退款或提现需满足平台当前规则和账户状态要求。",
      "具体可退金额、赠送金影响、未完结订单和申请状态需要通过业务系统查询后确认。"
    ],
    "negativeContextIds": ["refund_arrival_001#main"],
    "notes": "高风险资金问题，RAG 只说明规则。"
  }
]

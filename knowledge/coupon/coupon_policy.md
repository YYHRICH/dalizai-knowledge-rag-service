---
docId: doc_coupon_policy_v1
docTitle: 卡券使用规则
businessDomain: coupon
knowledgeType: coupon_policy
riskLevel: high
status: active
ownerTeam: 用户运营
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

# 卡券使用规则

## coupon_stack_001｜卡券是否可以叠加使用？

### Summary
部分卡券不可叠加使用，具体以活动页面、卡券详情页和订单结算页展示为准。

### Content
卡券是否可以叠加使用，需要以活动页面、卡券详情页和订单结算页展示为准。部分活动卡券不可与其他优惠叠加。如果订单结算页未展示某张卡券，说明当前订单可能不满足该卡券使用条件。

### Allowed Claims
- 部分卡券不可叠加使用，具体以活动页面、卡券详情页和订单结算页展示为准。
- 如果订单结算页未展示某张卡券，说明当前订单可能不满足该卡券使用条件。

### Forbidden Claims
- 所有卡券都可以叠加使用。
- 一定可以叠加使用。
- 可以绕过活动规则使用卡券。

### Keywords
- 卡券
- 优惠券
- 叠加
- 活动规则

### Similar Questions
- 优惠券能叠加吗？
- 两张券能一起用吗？
- 活动券可以同时用吗？

### Eval Questions
[
  {
    "question": "优惠券能不能叠加？",
    "referenceAnswer": "部分卡券不可叠加使用，具体以活动页面、卡券详情页和订单结算页展示为准。如果订单结算页未展示某张卡券，说明当前订单可能不满足该卡券使用条件。",
    "expectedContextIds": ["coupon_stack_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "部分卡券不可叠加使用，具体以活动页面、卡券详情页和订单结算页展示为准。",
      "如果订单结算页未展示某张卡券，说明当前订单可能不满足该卡券使用条件。"
    ],
    "negativeContextIds": [],
    "notes": "高风险规则，参考回答不能承诺一定可叠加。"
  }
]

## coupon_not_show_001｜为什么卡券没有展示？

### Summary
卡券未展示可能与适用站点、使用时间、订单条件、活动规则或卡券状态有关。

### Content
如果用户在结算页没有看到某张卡券，可能是当前订单不满足卡券的使用条件，例如适用站点、使用时间、最低消费、活动范围、卡券有效期或卡券状态等。具体能否使用应以卡券详情页和订单结算页展示为准。

### Allowed Claims
- 卡券未展示可能与适用站点、使用时间、订单条件、活动规则或卡券状态有关。
- 具体能否使用应以卡券详情页和订单结算页展示为准。

### Forbidden Claims
- 没展示的卡券一定可以补用。
- 可以人工强制使用不符合条件的卡券。
- 一定是系统错误导致卡券不展示。

### Keywords
- 卡券不显示
- 优惠券没有
- 不能用券
- 结算页

### Similar Questions
- 为什么我的优惠券用不了？
- 结算页看不到券怎么办？
- 卡券不显示是什么原因？

### Eval Questions
[
  {
    "question": "为什么我的优惠券用不了？",
    "referenceAnswer": "卡券未展示可能与适用站点、使用时间、订单条件、活动规则或卡券状态有关。具体能否使用应以卡券详情页和订单结算页展示为准。",
    "expectedContextIds": ["coupon_not_show_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "卡券未展示可能与适用站点、使用时间、订单条件、活动规则或卡券状态有关。",
      "具体能否使用应以卡券详情页和订单结算页展示为准。"
    ],
    "negativeContextIds": ["coupon_stack_001#main"],
    "notes": "区分卡券叠加和卡券不展示。"
  }
]

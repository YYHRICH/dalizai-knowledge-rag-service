---
docId: doc_invoice_operation_guide_v1
docTitle: 发票操作指引
businessDomain: invoice
knowledgeType: operation_guide
riskLevel: medium
status: active
ownerTeam: 财务运营
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

# 发票操作指引

## guide_invoice_apply_001｜怎么申请发票？

### Summary
用户可在小程序订单或发票入口查看可开票订单，并按页面提示申请发票。

### Content
用户可以进入小程序订单页面或发票相关入口，查看可开票订单，并按页面提示填写或确认发票信息后提交申请。是否可开票、可开票金额和申请状态以订单与发票系统展示为准。

### Allowed Claims
- 用户可在小程序订单页面或发票入口查看可开票订单。
- 是否可开票、可开票金额和申请状态以订单与发票系统展示为准。
- 用户可按页面提示填写或确认发票信息后提交申请。

### Forbidden Claims
- 所有订单都可以开票。
- 可以开出超过订单金额的发票。
- 未查询系统时承诺发票已经开具。

### Keywords
- 发票
- 开票
- 可开票订单
- 发票申请

### Similar Questions
- 怎么开发票？
- 订单可以开票吗？
- 发票在哪里申请？

### Eval Questions
[
  {
    "question": "怎么申请发票？",
    "referenceAnswer": "用户可在小程序订单页面或发票入口查看可开票订单。是否可开票、可开票金额和申请状态以订单与发票系统展示为准。用户可按页面提示填写或确认发票信息后提交申请。",
    "expectedContextIds": ["guide_invoice_apply_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "用户可在小程序订单页面或发票入口查看可开票订单。",
      "是否可开票、可开票金额和申请状态以订单与发票系统展示为准。"
    ],
    "negativeContextIds": [],
    "notes": "发票申请操作指引。"
  }
]

## guide_invoice_title_001｜发票抬头填错怎么办？

### Summary
发票抬头填写或修改规则需以发票页面和客服处理规则为准。

### Content
如果用户发现发票抬头填写错误，应先查看小程序发票页面是否支持修改、撤回或重新申请。已经开具的发票是否可以修改，需要结合发票状态和平台规则确认，必要时联系人工客服处理。

### Allowed Claims
- 发票抬头填写错误时，应先查看发票页面是否支持修改、撤回或重新申请。
- 已经开具的发票是否可以修改，需要结合发票状态和平台规则确认。
- 必要时可以联系人工客服处理。

### Forbidden Claims
- 已开具发票一定可以修改。
- 可以随意修改发票金额或主体。
- 未查询发票状态时承诺可以重开。

### Keywords
- 发票抬头
- 抬头填错
- 重开
- 修改发票

### Similar Questions
- 发票抬头填错怎么办？
- 已经开的发票能改吗？
- 发票能重开吗？

### Eval Questions
[
  {
    "question": "发票抬头填错了能改吗？",
    "referenceAnswer": "发票抬头填写错误时，应先查看发票页面是否支持修改、撤回或重新申请。已经开具的发票是否可以修改，需要结合发票状态和平台规则确认，必要时可以联系人工客服处理。",
    "expectedContextIds": ["guide_invoice_title_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "发票抬头填写错误时，应先查看发票页面是否支持修改、撤回或重新申请。",
      "已经开具的发票是否可以修改，需要结合发票状态和平台规则确认。"
    ],
    "negativeContextIds": ["guide_invoice_apply_001#main"],
    "notes": "发票修改边界。"
  }
]

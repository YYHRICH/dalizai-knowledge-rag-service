---
docId: doc_charging_operation_guide_v1
docTitle: 充电操作指引
businessDomain: charging
knowledgeType: operation_guide
riskLevel: low
status: active
ownerTeam: 用户运营
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

# 充电操作指引

## guide_charge_prepare_001｜充电前需要准备什么？

### Summary
充电前建议确认车辆已停稳、枪线可连接、小程序账户状态正常，并按站点提示操作。

### Content
用户充电前应确认车辆已停稳在对应车位，充电枪和车辆接口能够正常连接，并保持小程序登录状态。不同站点可能存在停车、地锁或场站管理规则，用户应按现场提示和小程序页面指引操作。

### Allowed Claims
- 充电前建议确认车辆已停稳并能正常连接充电枪。
- 用户应保持小程序登录状态，并按页面和现场提示操作。
- 不同站点可能存在停车、地锁或场站管理规则。

### Forbidden Claims
- 不登录小程序也可以启动充电。
- 可以忽略现场安全提示操作。

### Keywords
- 充电前
- 准备
- 连接枪
- 车辆接口

### Similar Questions
- 充电前要准备什么？
- 到站了怎么操作？
- 连接枪之前要注意什么？

### Eval Questions
[
  {
    "question": "充电前需要准备什么？",
    "referenceAnswer": "充电前建议确认车辆已停稳并能正常连接充电枪，保持小程序登录状态，并按页面和现场提示操作。不同站点可能存在停车、地锁或场站管理规则。",
    "expectedContextIds": ["guide_charge_prepare_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "充电前建议确认车辆已停稳并能正常连接充电枪。",
      "用户应保持小程序登录状态，并按页面和现场提示操作。"
    ],
    "negativeContextIds": [],
    "notes": "充电前准备操作指引。"
  }
]

## guide_charge_reservation_001｜可以预约充电吗？

### Summary
预约充电能力是否开放以小程序页面展示为准，未开放时用户可直接到站扫码启动充电。

### Content
如小程序页面展示预约入口，用户可以按页面提示选择站点、时间和充电设备进行预约。如页面未展示预约入口，表示当前渠道或站点暂不支持预约能力，用户可以到站后按扫码充电流程启动。预约成功与否以页面最终确认结果为准。

### Allowed Claims
- 预约充电能力是否开放以小程序页面展示为准。
- 如页面未展示预约入口，用户可以到站后按扫码充电流程启动。
- 预约成功与否以页面最终确认结果为准。

### Forbidden Claims
- 所有站点都支持预约充电。
- 可以保证预约一定成功。
- 可以为用户私下占用充电桩。

### Keywords
- 预约充电
- 预定
- 占桩
- 预约入口

### Similar Questions
- 能不能预约充电？
- 可以提前占桩吗？
- 怎么预约一个充电桩？

### Eval Questions
[
  {
    "question": "可以预约充电桩吗？",
    "referenceAnswer": "预约充电能力是否开放以小程序页面展示为准。如页面未展示预约入口，用户可以到站后按扫码充电流程启动。预约成功与否以页面最终确认结果为准。",
    "expectedContextIds": ["guide_charge_reservation_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "预约充电能力是否开放以小程序页面展示为准。",
      "预约成功与否以页面最终确认结果为准。"
    ],
    "negativeContextIds": ["faq_charge_scan_001#main"],
    "notes": "预约规则指引，不承诺一定成功。"
  }
]

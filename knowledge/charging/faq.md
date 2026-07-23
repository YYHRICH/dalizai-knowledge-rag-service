---
docId: doc_charging_faq_v1
docTitle: 充电常见问题
businessDomain: charging
knowledgeType: faq
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

# 充电常见问题

## faq_charge_scan_001｜怎么扫码充电？

### Summary
用户连接充电枪后，可以通过小程序扫码启动充电。

### Content
用户到达站点后，需要先将充电枪正确连接车辆，再进入大力仔小程序首页或充电页面，点击扫码充电并扫描设备二维码。系统会在启动前检查账户状态、余额、设备可用性等条件；如余额不足、设备不可用或二维码异常，页面会给出提示。

### Allowed Claims
- 用户连接充电枪后，可以在小程序中扫码启动充电。
- 余额不足或设备不可用时，系统会在启动前提示。
- 二维码异常时，可以根据页面提示重新扫码、手动输入设备编号或联系人工客服。

### Forbidden Claims
- 一定可以启动成功。
- 可以绕过余额校验启动。
- 二维码异常时一定是设备故障。

### Keywords
- 扫码
- 二维码
- 启动充电
- 连接充电枪

### Similar Questions
- 怎么扫码充电？
- 第一次用大力仔怎么开始充电？
- 扫哪里可以启动充电？

### Eval Questions
[
  {
    "question": "怎么扫码充电？",
    "referenceAnswer": "用户连接充电枪后，可以在小程序中扫码启动充电。余额不足或设备不可用时，系统会在启动前提示。",
    "expectedContextIds": ["faq_charge_scan_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "用户连接充电枪后，可以在小程序中扫码启动充电。",
      "余额不足或设备不可用时，系统会在启动前提示。"
    ],
    "negativeContextIds": ["faq_charge_stop_001#main"],
    "notes": "扫码启动充电核心 FAQ。"
  },
  {
    "question": "第一次用这个桩怎么开始？",
    "referenceAnswer": "用户连接充电枪后，可以进入大力仔小程序扫码启动充电。若余额不足或设备不可用，系统会在启动前提示。",
    "expectedContextIds": ["faq_charge_scan_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "用户连接充电枪后，可以在小程序中扫码启动充电。",
      "余额不足或设备不可用时，系统会在启动前提示。"
    ],
    "negativeContextIds": [],
    "notes": "口语化启动充电问法。"
  }
]

## faq_charge_stop_001｜怎么结束充电？

### Summary
用户可以在小程序当前充电订单页面按提示结束充电。

### Content
充电过程中，用户可以进入小程序当前充电订单页面，按页面提示结束充电。结束充电后，系统会根据实际充电情况生成订单。若页面无法结束充电或设备状态异常，用户可以根据页面提示重试或联系人工客服协助处理。

### Allowed Claims
- 用户可以在小程序当前充电订单页面按提示结束充电。
- 结束充电后，系统会根据实际充电情况生成订单。
- 页面无法结束充电时，可以根据页面提示重试或联系人工客服。

### Forbidden Claims
- 可以不按页面提示强制结束充电。
- 结束充电后一定不会产生费用。
- 页面无法结束时一定是设备损坏。

### Keywords
- 结束充电
- 停止充电
- 充电订单
- 停止订单

### Similar Questions
- 怎么停止充电？
- 不想充了怎么结束？
- 充电怎么关掉？

### Eval Questions
[
  {
    "question": "怎么结束充电？",
    "referenceAnswer": "用户可以在小程序当前充电订单页面按提示结束充电。结束充电后，系统会根据实际充电情况生成订单。",
    "expectedContextIds": ["faq_charge_stop_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "用户可以在小程序当前充电订单页面按提示结束充电。",
      "结束充电后，系统会根据实际充电情况生成订单。"
    ],
    "negativeContextIds": ["faq_charge_scan_001#main"],
    "notes": "区分启动充电和结束充电。"
  }
]

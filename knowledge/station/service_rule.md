---
docId: doc_station_service_rule_v1
docTitle: 站点服务规则
businessDomain: station
knowledgeType: service_rule
riskLevel: medium
status: active
ownerTeam: 场站运营
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

# 站点服务规则

## rule_station_parking_001｜充电站停车费怎么算？

### Summary
停车费规则以站点现场公示、停车场规则和小程序页面展示为准。

### Content
不同站点的停车费规则可能不同，具体以站点现场公示、停车场管理规则和小程序页面展示为准。部分站点可能提供充电减免停车费或限时免费政策，是否适用需要以站点页面或现场规则为准。

### Allowed Claims
- 停车费规则以站点现场公示、停车场规则和小程序页面展示为准。
- 部分站点可能有停车费减免或限时免费政策，是否适用需以站点页面或现场规则为准。

### Forbidden Claims
- 所有站点都免停车费。
- 充电后一定可以免停车费。
- 可以绕过停车场收费规则。

### Keywords
- 停车费
- 停车规则
- 减免
- 场站

### Similar Questions
- 充电要停车费吗？
- 停车费能免吗？
- 这个站停车怎么收费？

### Eval Questions
[
  {
    "question": "充电站停车费怎么算？",
    "referenceAnswer": "停车费规则以站点现场公示、停车场规则和小程序页面展示为准。部分站点可能有停车费减免或限时免费政策，是否适用需以站点页面或现场规则为准。",
    "expectedContextIds": ["rule_station_parking_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "停车费规则以站点现场公示、停车场规则和小程序页面展示为准。",
      "部分站点可能有停车费减免或限时免费政策，是否适用需以站点页面或现场规则为准。"
    ],
    "negativeContextIds": [],
    "notes": "停车费规则不能统一承诺免费。"
  }
]

## rule_station_navigation_001｜找不到站点怎么办？

### Summary
找不到站点时，用户可以查看小程序站点地址、导航入口、场站备注和现场标识。

### Content
如果用户到达附近但找不到站点，可以先查看小程序中的站点地址、导航入口、场站备注和现场标识。部分站点位于地下停车场、园区或商业综合体内部，建议根据页面备注和现场指引进入。

### Allowed Claims
- 找不到站点时，可以查看小程序站点地址、导航入口、场站备注和现场标识。
- 部分站点可能位于地下停车场、园区或商业综合体内部。

### Forbidden Claims
- 导航位置一定完全准确。
- 可以进入任何限制区域寻找设备。

### Keywords
- 找不到站
- 导航
- 地址
- 场站备注

### Similar Questions
- 找不到充电站怎么办？
- 导航到了但没看到桩？
- 站点在哪里？

### Eval Questions
[
  {
    "question": "导航到了但找不到充电站怎么办？",
    "referenceAnswer": "找不到站点时，可以查看小程序站点地址、导航入口、场站备注和现场标识。部分站点可能位于地下停车场、园区或商业综合体内部。",
    "expectedContextIds": ["rule_station_navigation_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "找不到站点时，可以查看小程序站点地址、导航入口、场站备注和现场标识。",
      "部分站点可能位于地下停车场、园区或商业综合体内部。"
    ],
    "negativeContextIds": [],
    "notes": "站点导航规则。"
  }
]

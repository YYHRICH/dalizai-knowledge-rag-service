---
docId: doc_device_troubleshooting_v1
docTitle: 设备故障排查
businessDomain: device
knowledgeType: troubleshooting
riskLevel: medium
status: active
ownerTeam: 设备运营
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

# 设备故障排查

## trouble_qrcode_scan_001｜二维码扫不出来怎么办？

### Summary
二维码无法识别时，可以检查摄像头权限、二维码遮挡、光线和扫码距离。

### Content
如果设备二维码无法识别，用户可以先检查手机摄像头权限是否开启，二维码是否被遮挡、污损，现场光线是否过暗或反光，并调整扫码距离。如果仍无法识别，可根据页面提示尝试手动输入设备编号，或联系人工客服协助处理。

### Allowed Claims
- 二维码无法识别时，可以先检查摄像头权限、二维码遮挡、光线和扫码距离。
- 如果仍无法识别，可以按页面提示尝试手动输入设备编号或联系人工客服。

### Forbidden Claims
- 一定是设备损坏。
- 可以绕过设备校验启动充电。

### Keywords
- 二维码
- 扫码失败
- 扫不出来
- 设备编号

### Similar Questions
- 二维码扫不出来怎么办？
- 扫码没反应怎么办？
- 扫二维码一直失败？

### Eval Questions
[
  {
    "question": "二维码扫不出来怎么办？",
    "referenceAnswer": "二维码无法识别时，可以先检查摄像头权限、二维码遮挡、光线和扫码距离。如果仍无法识别，可以按页面提示尝试手动输入设备编号或联系人工客服。",
    "expectedContextIds": ["trouble_qrcode_scan_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "二维码无法识别时，可以先检查摄像头权限、二维码遮挡、光线和扫码距离。",
      "如果仍无法识别，可以按页面提示尝试手动输入设备编号或联系人工客服。"
    ],
    "negativeContextIds": ["faq_charge_scan_001#main"],
    "notes": "区分正常扫码充电和二维码故障排查。"
  }
]

## trouble_connector_locked_001｜充电枪拔不下来怎么办？

### Summary
充电枪拔不下来时，用户应先确认订单是否已结束，并按车辆和设备提示安全处理。

### Content
如果充电枪暂时无法拔下，用户应先确认小程序订单是否已结束、车辆是否已解锁充电口，并查看设备或车辆页面提示。不要强行拉拽枪线，以免造成设备或车辆接口损坏。若按提示操作后仍无法拔下，应联系人工客服或现场工作人员协助处理。

### Allowed Claims
- 充电枪拔不下来时，应先确认订单是否已结束、车辆是否已解锁充电口。
- 不建议强行拉拽枪线。
- 按提示操作后仍无法拔下时，可以联系人工客服或现场工作人员协助处理。

### Forbidden Claims
- 可以强行拔枪。
- 一定是平台设备故障。
- 一定可以远程立即解锁。

### Keywords
- 枪拔不下
- 充电枪
- 枪线
- 解锁

### Similar Questions
- 充电枪拔不下来怎么办？
- 枪锁住了怎么办？
- 结束充电后拔不了枪？

### Eval Questions
[
  {
    "question": "充电枪拔不下来怎么办？",
    "referenceAnswer": "充电枪拔不下来时，应先确认订单是否已结束、车辆是否已解锁充电口。不建议强行拉拽枪线。按提示操作后仍无法拔下时，可以联系人工客服或现场工作人员协助处理。",
    "expectedContextIds": ["trouble_connector_locked_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "充电枪拔不下来时，应先确认订单是否已结束、车辆是否已解锁充电口。",
      "不建议强行拉拽枪线。"
    ],
    "negativeContextIds": [],
    "notes": "设备安全类故障排查。"
  }
]

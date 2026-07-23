# 业务知识 Markdown 模拟数据集需求 v0.1

## 1. 目标

请业务或 Agent 开发同事协助生成一批模拟业务知识 Markdown，用于独立知识 RAG 服务的解析、入库、检索和评测。

这份数据不是 Agent 调用 case，而是模拟未来业务人员维护的知识库内容。也就是说，请按本文格式写 Markdown 文件。

## 2. 交付方式

请按业务域创建多个 Markdown 文件，建议目录结构：

```text
knowledge/
  charging/
    faq.md
    operation_guide.md
    troubleshooting.md
  device/
    troubleshooting.md
  station/
    service_rule.md
  payment/
    billing_policy.md
  coupon/
    coupon_policy.md
  refund/
    refund_policy.md
  invoice/
    operation_guide.md
  account/
    faq.md
  customer_service/
    handoff_guide.md
    risk_notice.md
```

第一批建议提供 10-30 条知识，优先覆盖扫码充电、结束充电、卡券、退款、扣费规则、二维码异常、停车费、发票、转人工等高频场景。

为了后续按 Ragas 四项核心指标评测，每条模拟知识建议同时提供 `Eval Questions`。这些评测问题不会作为正式知识返回给用户，只用于构造评测集。

## 3. 文档级 Front Matter

每个 Markdown 文件顶部必须有 YAML front matter。

```yaml
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
```

必填字段：

```text
docId
docTitle
businessDomain
knowledgeType
status
ownerTeam
effectiveFrom
updatedAt
reviewDueAt
```

可选字段：

```text
riskLevel
owner
effectiveTo
channels
cityCodes
stationIds
```

默认规则：

```text
riskLevel 不填默认 medium
channels 为空表示所有渠道通用
cityCodes 为空表示城市通用
stationIds 为空表示站点通用
effectiveTo 为空表示长期有效
```

## 4. 业务域枚举

```text
charging            充电流程与充电行为
device              充电设备、枪线、二维码、设备异常
station             站点、停车、导航、场站规则
payment             支付、扣费、余额、账单说明
coupon              卡券、优惠券、活动优惠
refund              退款规则、退款说明
invoice             发票
account             登录、账户、手机号、个人信息
order               订单说明、订单展示、订单入口
customer_service    人工客服、转人工规则、投诉入口
general             通用说明
```

## 5. 知识类型枚举

```text
faq                 常见问答
operation_guide     操作指引
billing_policy      计费/扣费规则
coupon_policy       卡券/活动/优惠规则
refund_policy       退款规则
troubleshooting     故障排查
handoff_guide       转人工指引
service_rule        平台服务规则、使用规则
risk_notice         风险提示、禁止承诺、免责声明
```

## 6. riskLevel 枚举

```text
low       普通 FAQ、操作说明
medium    服务规则、故障排查、账户说明
high      计费、退款、优惠、活动、风险提示
critical  赔偿、法律、重大安全、强监管内容
```

第一版约束：

- `riskLevel=critical` 且 `status=active` 的知识禁止入库。
- `riskLevel=high` 时，`Forbidden Claims` 必须填写。
- `riskLevel=low/medium` 时，`Forbidden Claims` 可为空。

## 7. Ragas 评测适配要求

后续我们会重点参考 Ragas 的四类 RAG 指标：

| 指标 | 评估目标 | 数据集中需要支持的内容 |
| --- | --- | --- |
| Faithfulness | 生成回答是否忠实于检索上下文 | `Allowed Claims`、`referenceAnswer`、期望上下文 |
| Answer / Response Relevancy | 回答是否回应用户问题 | `question`、`referenceAnswer` |
| Context Precision | 检索出来的上下文是否少噪声、排序是否靠前 | `expectedContextIds`、可选 `negativeContextIds` |
| Context Recall | 是否召回了回答所需的关键上下文 | `referenceAnswer`、`expectedContextIds` |

因此，模拟 Markdown 不只要写知识正文，还要为每条知识补充 1-3 个评测问题。

评测问题写在条目内的 `### Eval Questions` 小节，使用 JSON 数组：

```json
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
    "negativeContextIds": [],
    "notes": "用于评测扫码充电 FAQ 的召回和回答相关性。"
  }
]
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `question` | string | 是 | 用户可能提出的问题 |
| `referenceAnswer` | string | 是 | 标准参考回答，必须只基于 `Allowed Claims` 和 `Content` |
| `expectedContextIds` | string[] | 是 | 期望召回的 chunkId，默认 `{knowledgeId}#main` |
| `expectedStatus` | string | 是 | `success` / `low_confidence` / `not_found` |
| `expectedClaims` | string[] | 是 | 参考回答应覆盖的事实点，通常来自 `Allowed Claims` |
| `negativeContextIds` | string[] | 否 | 明确不应排在前面的无关或易混淆上下文 |
| `notes` | string | 否 | 补充说明 |

写作规则：

- 每条知识至少提供 1 个 `Eval Questions`。
- FAQ 和高频问题建议提供 2-3 个不同问法。
- `referenceAnswer` 不能包含 `Forbidden Claims` 禁止的内容。
- `referenceAnswer` 不要写订单金额、余额、退款进度、设备实时状态等业务真值。
- 对于不应由 RAG 回答的问题，可以单独放到评测集，不建议写在某条 active 知识的 `Eval Questions` 中。

## 8. 知识条目格式

一个二级标题是一条知识：

```markdown
## faq_charge_scan_001｜怎么扫码充电？

### Summary
用户连接充电枪后，可以通过小程序扫码启动充电。

### Content
用户连接充电枪后，可在小程序首页点击扫码充电，扫描设备二维码并确认启动。余额不足或设备不可用时，系统会在启动前提示。

### Allowed Claims
- 用户连接充电枪后，可以在小程序中扫码启动充电。
- 余额不足或设备不可用时，系统会在启动前提示。

### Forbidden Claims
- 一定可以启动成功。
- 可以绕过余额校验启动。

### Keywords
- 扫码
- 二维码
- 启动充电

### Similar Questions
- 扫哪里充电？
- 怎么扫二维码启动？
- 不会扫码充电怎么办？

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
    "negativeContextIds": [],
    "notes": "扫码充电核心 FAQ。"
  }
]
```

条目级必填：

```text
knowledgeId
title
Summary
Content
Allowed Claims
```

条目级可选：

```text
Forbidden Claims
Keywords
Similar Questions
```

模拟数据集额外要求：

```text
Eval Questions
```

`Eval Questions` 用于后续 Ragas 评测，不属于正式对客知识。生产知识库后续可以不要求业务人员填写，但本次模拟数据集请尽量填写。

第一版不支持条目级 YAML metadata。条目继承文档级 metadata。如果某条知识需要不同风险等级、生效期、负责人、渠道、城市或站点范围，请拆到另一个 Markdown 文件。

## 9. knowledgeId 命名规则

规则：

```text
全局唯一
小写字母、数字、下划线
建议格式：{typePrefix}_{topic}_{seq}
不强制包含 businessDomain
已发布后不建议修改
```

类型前缀：

```text
faq       FAQ
guide     操作指引
bill      计费/扣费规则
coupon    卡券/活动规则
refund    退款规则
trouble   故障排查
handoff   转人工指引
rule      服务规则
risk      风险提示
```

示例：

```text
faq_charge_scan_001
guide_start_charge_001
bill_deduction_rule_001
coupon_stack_001
refund_arrival_001
trouble_qrcode_scan_001
handoff_unanswerable_001
rule_station_parking_001
risk_compensation_commitment_001
```

## 10. 写作规则

### Summary

- 必填。
- 一句话摘要。
- 不超过 120 字。

### Content

- 必填。
- 写知识正文，不写内部敏感信息。
- 建议不超过 1500 字。
- 如果超过 3000 字，建议拆成多条知识。

### Allowed Claims

- 必填，至少 1 条。
- 必须是可以直接对客表达的事实点。
- 每条尽量一句话。
- 不写内部流程、内部系统名、内部判断逻辑。
- 不写无依据的模糊结论。

### Forbidden Claims

- 高风险知识必填。
- 用来约束 Agent 不能说什么。
- 例如不能承诺“一定成功”“一定退款”“一定赔偿”。

### Keywords

- 建议填写。
- FAQ 建议至少 2 个。
- 非 FAQ 建议至少 2 个。

### Similar Questions

- FAQ 建议至少 2 条。
- 非 FAQ 可选。
- 尽量写真实用户口语化问法。

## 11. 示例文件一：knowledge/charging/faq.md

```markdown
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
用户连接充电枪后，可在小程序首页点击扫码充电，扫描设备二维码并确认启动。余额不足或设备不可用时，系统会在启动前提示。

### Allowed Claims
- 用户连接充电枪后，可以在小程序中扫码启动充电。
- 余额不足或设备不可用时，系统会在启动前提示。

### Forbidden Claims
- 一定可以启动成功。
- 可以绕过余额校验启动。

### Keywords
- 扫码
- 二维码
- 启动充电

### Similar Questions
- 扫哪里充电？
- 怎么扫二维码启动？
- 不会扫码充电怎么办？

## faq_charge_stop_001｜怎么结束充电？

### Summary
用户可以在小程序当前充电订单页面结束充电。

### Content
充电过程中，用户可以进入小程序当前充电订单页面，按页面提示结束充电。结束后系统会根据实际充电情况生成订单。

### Allowed Claims
- 用户可以在小程序当前充电订单页面按提示结束充电。
- 结束充电后，系统会根据实际充电情况生成订单。

### Forbidden Claims
- 可以不按页面提示强制结束充电。

### Keywords
- 结束充电
- 停止充电
- 充电订单

### Similar Questions
- 怎么停止充电？
- 充电怎么关掉？
- 不想充了怎么结束？

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
```

## 12. 示例文件二：knowledge/coupon/coupon_policy.md

```markdown
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
reviewDueAt: 2026-08-07T00:00:00+08:00
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
```

## 13. 示例文件三：knowledge/refund/refund_policy.md

```markdown
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
退款到账时间受支付渠道和银行处理时效影响，具体到账进度需以业务系统查询结果为准。

### Content
退款申请提交后，到账时间会受支付渠道、银行或第三方支付机构处理时效影响。用户如需确认某笔退款的实时进度，应通过业务系统查询后确认。

### Allowed Claims
- 退款到账时间会受支付渠道、银行或第三方支付机构处理时效影响。
- 某笔退款的实时进度需要通过业务系统查询后确认。

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
    "referenceAnswer": "退款到账时间会受支付渠道、银行或第三方支付机构处理时效影响。某笔退款的实时进度需要通过业务系统查询后确认。",
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
```

## 14. 示例文件四：knowledge/device/troubleshooting.md

```markdown
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
reviewDueAt: 2026-09-06T00:00:00+08:00
channels:
  - wechat_mini_program
cityCodes:
stationIds:
---

# 设备故障排查

## trouble_qrcode_scan_001｜二维码扫不出来怎么办？

### Summary
二维码无法识别时，用户可以检查光线、距离、摄像头权限，并尝试手动输入设备编号或联系人工客服。

### Content
如果设备二维码无法识别，用户可以先检查手机摄像头权限、二维码是否被遮挡、光线是否过暗或反光，并调整扫码距离。如果仍无法识别，可根据页面提示尝试手动输入设备编号，或联系人工客服协助处理。

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
```

## 15. 示例文件五：knowledge/customer_service/handoff_guide.md

```markdown
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
reviewDueAt: 2026-09-06T00:00:00+08:00
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
如果用户问题涉及订单金额、退款进度、设备实时状态、赔偿承诺、法律责任判断，或当前知识库无法提供可靠依据，应引导用户联系人工客服进一步确认。

### Allowed Claims
- 这个问题需要结合具体情况进一步确认，建议联系人工客服处理。
- 涉及订单、退款或设备实时状态的问题，需要通过业务系统查询后确认。

### Forbidden Claims
- 直接承诺赔偿金额。
- 在没有业务系统结果时判断订单、退款或设备实时状态。

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
    "referenceAnswer": "这个问题需要结合具体情况进一步确认，建议联系人工客服处理。涉及订单、退款或设备实时状态的问题，需要通过业务系统查询后确认。",
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
```

## 16. 不应写入 RAG 的内容

以下内容不要写入 active 知识：

- 赔偿金额或赔偿承诺
- 法律责任判断
- 未发布活动或未生效政策
- 内部运营/客服考核话术
- 用户隐私数据
- 商业敏感数据
- 设备后台诊断细节
- 订单金额、账户余额、退款进度、设备实时状态等业务真值

如需描述边界，请写成转人工或调用业务 MCP 的指引，而不是给出具体结论。

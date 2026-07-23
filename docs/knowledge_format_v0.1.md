# Markdown 知识库格式 v0.1

## 组织方式

按业务域组织 Markdown 文件。一个 Markdown 文件是一个知识集合，一个二级标题是一条知识。

```text
knowledge/
  charging/
    faq.md
    operation_guide.md
    troubleshooting.md
  payment/
    billing_policy.md
    coupon_policy.md
    refund_policy.md
```

## 文档级元信息

```yaml
---
docId: doc_charging_faq_v1
docTitle: 充电常见问题
businessDomain: charging
knowledgeType: faq
status: active
ownerTeam: 用户运营
effectiveFrom: 2026-07-23T00:00:00+08:00
effectiveTo:
reviewDueAt: 2026-10-23T00:00:00+08:00
channels:
  - wechat_mini_program
---
```

必填字段：

- `docId`
- `docTitle`
- `businessDomain`
- `knowledgeType`
- `status`
- `ownerTeam`
- `effectiveFrom`
- `reviewDueAt`

只有 `status=active` 且在有效期内的文档参与检索。

## 条目格式

```markdown
## faq_charge_scan_001｜怎么扫码充电？

### Summary
用户连接充电枪后，可以通过小程序扫码启动充电。

### Content
用户连接充电枪后，可在小程序首页点击扫码充电，扫描设备二维码并确认启动。

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
```

条目级必填：

- `knowledgeId`: 来自二级标题 `## knowledgeId｜标题`
- `title`
- `Summary`
- `Content`
- `Allowed Claims`

条目级可选：

- `Forbidden Claims`
- `Keywords`
- `Similar Questions`
- `Cards`

## Embedding 文本

第一版参与 embedding 的字段：

- `title`
- `businessDomain`
- `knowledgeType`
- `summary`
- `keywords`
- `similarQuestions`
- `content`
- `allowedClaims`

`forbiddenClaims` 不参与 embedding，只作为安全约束返回给 Agent。

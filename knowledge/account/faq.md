---
docId: doc_account_faq_v1
docTitle: 账户常见问题
businessDomain: account
knowledgeType: faq
riskLevel: medium
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

# 账户常见问题

## faq_account_login_001｜登录不上怎么办？

### Summary
登录异常时，用户可以检查手机号、验证码、网络和小程序登录状态。

### Content
如果用户无法登录小程序，可以先确认手机号是否正确、验证码是否有效、网络是否正常，并尝试重新进入小程序。若仍无法登录，可根据页面提示处理或联系人工客服协助核验账户状态。

### Allowed Claims
- 登录异常时，可以先确认手机号、验证码、网络和小程序状态。
- 仍无法登录时，可以根据页面提示处理或联系人工客服协助核验账户状态。

### Forbidden Claims
- 可以绕过登录使用个人账户功能。
- 一定是账号被封禁。

### Keywords
- 登录
- 验证码
- 手机号
- 账户

### Similar Questions
- 登录不上怎么办？
- 收不到验证码怎么办？
- 小程序进不去账户？

### Eval Questions
[
  {
    "question": "登录不上怎么办？",
    "referenceAnswer": "登录异常时，可以先确认手机号、验证码、网络和小程序状态。仍无法登录时，可以根据页面提示处理或联系人工客服协助核验账户状态。",
    "expectedContextIds": ["faq_account_login_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "登录异常时，可以先确认手机号、验证码、网络和小程序状态。",
      "仍无法登录时，可以根据页面提示处理或联系人工客服协助核验账户状态。"
    ],
    "negativeContextIds": [],
    "notes": "账户登录 FAQ。"
  }
]

## faq_account_phone_change_001｜手机号换了怎么办？

### Summary
手机号变更需以小程序账户页面支持能力和客服核验规则为准。

### Content
如果用户需要更换绑定手机号，应先查看小程序账户页面是否支持修改。涉及账户安全的信息变更可能需要身份核验，具体处理方式以页面提示和客服核验规则为准。

### Allowed Claims
- 更换绑定手机号应先查看小程序账户页面是否支持修改。
- 涉及账户安全的信息变更可能需要身份核验。
- 具体处理方式以页面提示和客服核验规则为准。

### Forbidden Claims
- 可以绕过身份核验更换手机号。
- 未核验身份时承诺已经修改成功。

### Keywords
- 手机号
- 换绑
- 账户安全
- 身份核验

### Similar Questions
- 手机号换了怎么办？
- 怎么换绑定手机号？
- 原手机号不用了怎么登录？

### Eval Questions
[
  {
    "question": "怎么换绑定手机号？",
    "referenceAnswer": "更换绑定手机号应先查看小程序账户页面是否支持修改。涉及账户安全的信息变更可能需要身份核验。具体处理方式以页面提示和客服核验规则为准。",
    "expectedContextIds": ["faq_account_phone_change_001#main"],
    "expectedStatus": "success",
    "expectedClaims": [
      "更换绑定手机号应先查看小程序账户页面是否支持修改。",
      "涉及账户安全的信息变更可能需要身份核验。"
    ],
    "negativeContextIds": ["faq_account_login_001#main"],
    "notes": "账户安全边界。"
  }
]

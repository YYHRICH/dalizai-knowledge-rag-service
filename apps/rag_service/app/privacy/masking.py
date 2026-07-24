"""\u67e5\u8be2\u6587\u672c\u8131\u654f\u548c\u6807\u8bc6\u7b26\u54c8\u5e0c\u3002

\u5728\u5199\u5165\u5ba1\u8ba1\u65e5\u5fd7\u524d\uff0c\u5bf9\u53ef\u80fd\u5305\u542b\u4e2a\u4eba\u8eab\u4efd\u4fe1\u606f\uff08PII\uff09\u7684\u5b57\u6bb5\u8fdb\u884c\u5904\u7406\uff1a
- ``mask_text``: \u7528\u5360\u4f4d\u7b26\u66ff\u6362\u5339\u914d\u5230 PII \u6a21\u5f0f\u7684\u6587\u672c\u7247\u6bb5\u3002
- ``hash_identifier``: \u5bf9 sessionId/userId \u505a SHA-256 \u54c8\u5e0c + salt\uff0c\u652f\u6301\u53bb\u91cd\u5206\u6790\u4f46\u4e0d\u53ef\u9006\u3002
"""

from __future__ import annotations

import hashlib
import re

# \u2500\u2500 PII \u6b63\u5219\u8868\u8fbe\u5f0f \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
"""\u4e2d\u56fd\u5927\u9646\u624b\u673a\u53f7\uff0811 \u4f4d\uff0c1 \u5f00\u5934\uff09\u3002"""

ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
"""\u4e2d\u56fd\u5927\u9646\u8eab\u4efd\u8bc1\u53f7\uff0818 \u4f4d\uff0c\u672b\u4f4d\u53ef\u4ee5\u662f\u6570\u5b57\u6216 X\uff09\u3002"""

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
"""\u7535\u5b50\u90ae\u7bb1\u5730\u5740\u3002"""

ORDER_RE = re.compile(r"(?<![A-Za-z0-9])(?:ORDER|order|ORD|ord|NO|no)[-_]?[A-Za-z0-9]{6,}(?![A-Za-z0-9])")
"""\u8ba2\u5355\u7f16\u53f7\uff08ORDER/ord/NO/no \u524d\u7f00 + 6 \u4f4d\u4ee5\u4e0a\u5b57\u6bcd\u6570\u5b57\uff09\u3002"""

LONG_NUMBER_RE = re.compile(r"(?<!\d)\d{10,}(?!\d)")
"""\u957f\u6570\u5b57\u4e32\uff0810 \u4f4d\u4ee5\u4e0a\uff09\uff0c\u53ef\u80fd\u662f\u94f6\u884c\u5361\u53f7\u7b49\u3002"""

PLATE_RE = re.compile(r"[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}")
"""\u4e2d\u56fd\u5927\u9646\u8f66\u724c\u53f7\uff08\u7701\u4efd\u7b80\u79f0 + \u5b57\u6bcd + 5-6 \u4f4d\uff09\u3002"""


def mask_text(text: str | None) -> str | None:
    """\u5bf9\u6587\u672c\u4e2d\u7684 PII \u8fdb\u884c\u5360\u4f4d\u7b26\u66ff\u6362\u3002

    \u5339\u914d\u7c7b\u578b\uff1a\u624b\u673a\u53f7\u3001\u8eab\u4efd\u8bc1\u53f7\u3001\u90ae\u7bb1\u3001\u8ba2\u5355\u7f16\u53f7\u3001\u8f66\u724c\u53f7\u3001\u957f\u6570\u5b57\u4e32\u3002
    \u66ff\u6362\u540e\u7684\u5360\u4f4d\u7b26\u4f8b\u5982 ``[PHONE]``\u3001``[ID_CARD]`` \u7b49\u3002

    Args:
        text: \u9700\u8981\u8131\u654f\u7684\u539f\u59cb\u6587\u672c\u3002

    Returns:
        \u8131\u654f\u540e\u7684\u6587\u672c\u3002\u8f93\u5165\u4e3a None \u65f6\u8fd4\u56de None\u3002
    """
    if text is None:
        return None
    masked = PHONE_RE.sub("[PHONE]", text)
    masked = ID_CARD_RE.sub("[ID_CARD]", masked)
    masked = EMAIL_RE.sub("[EMAIL]", masked)
    masked = ORDER_RE.sub("[ORDER_ID]", masked)
    masked = PLATE_RE.sub("[PLATE]", masked)
    masked = LONG_NUMBER_RE.sub("[LONG_NUMBER]", masked)
    return masked


def hash_identifier(value: str | None, salt: str) -> str | None:
    """对标识符进行加盐 SHA-256 哈希。

    使用 ``sha256(salt + ":" + value)`` 的方式保证：
    - 同一标识符在不同 salt 下产生不同哈希（防止跨服务关联）。
    - 同一 salt 下同一标识符始终产生相同哈希（支持去重和计数分析）。
    - 不可逆（无法从哈希还原原始值）。

    Args:
        value: 待哈希的原始标识符。
        salt: 盐值，使用 RAG_SERVICE_API_KEY 作为 salt。

    Returns:
        hex 格式的哈希字符串。输入为 None 或空字符串时返回 None。
    """
    if value is None or value == "":
        return None
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return digest

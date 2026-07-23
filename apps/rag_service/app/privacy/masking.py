from __future__ import annotations

import hashlib
import re

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORDER_RE = re.compile(r"(?<![A-Za-z0-9])(?:ORDER|order|ORD|ord|NO|no)[-_]?[A-Za-z0-9]{6,}(?![A-Za-z0-9])")
LONG_NUMBER_RE = re.compile(r"(?<!\d)\d{10,}(?!\d)")
PLATE_RE = re.compile(r"[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}")


def mask_text(text: str | None) -> str | None:
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
    if value is None or value == "":
        return None
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return digest

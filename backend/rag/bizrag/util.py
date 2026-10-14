from __future__ import annotations

import re
from datetime import date


def months_ago(n: int, today: date | None = None) -> date:
    """n개월 전 같은 달의 1일."""
    t = today or date.today()
    y, m = t.year, t.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def to_float(v) -> float | None:
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    if s in ("", "-", "…", "x", "X"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


_DATE8 = re.compile(r"(20\d{2})[-./]?(\d{2})[-./]?(\d{2})")


def find_date8(text: str) -> str | None:
    """'..._20260630' 같은 문자열에서 YYYYMMDD를 찾는다."""
    m = _DATE8.search(text or "")
    return "".join(m.groups()) if m else None


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")

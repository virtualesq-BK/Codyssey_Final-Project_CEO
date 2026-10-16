"""
K-Startup 모집 중 공고 (공공데이터포털 '창업진흥원 K-Startup 사업공고' API) → 공고 찾기 화면용 목록

- A의 수집기(backend/api_catalog)와 같은 엔드포인트를 쓰되, 배포 서버(Render)는 디스크가 재시작 때 지워지므로
  DB 파일 대신 메모리에 두고 6시간마다 새로 받는다
- 키가 없거나 실패하면 None을 돌려주고, routes.py는 기존 샘플 공고로 돌아간다
- 마감 상태(모집중 / 마감임박(D-3) / 마감)는 읽을 때마다 오늘 기준으로 다시 계산한다
"""
from __future__ import annotations

import asyncio
import html
import logging
import time
from datetime import date, datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

ENDPOINT = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
DETAIL_URL = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={sn}"
TTL_SEC = 6 * 60 * 60
PAGE_SIZE = 100
MAX_PAGES = 10

_cache: dict[str, Any] = {"items": None, "at": 0.0}
_lock = asyncio.Lock()


def _service_key() -> str:
    from app.core.config import settings

    return settings.data_go_kr_service_key


def _day(v: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(v)[:8], "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def _clean(v: Any) -> str:
    s = "" if v is None else html.unescape(str(v)).strip()
    return "" if s in ("None", "null") else s


def deadline_status(ends_on: Optional[date], today: Optional[date] = None) -> str:
    if not ends_on:
        return "모집중"
    left = (ends_on - (today or date.today())).days
    if left < 0:
        return "마감"
    return "마감임박(D-3)" if left <= 3 else "모집중"


def to_program(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """API 한 건 → 공고 찾기 화면이 쓰는 모양 (routes.py 샘플과 같은 필드)"""
    title = _clean(raw.get("biz_pbanc_nm"))
    sn = _clean(raw.get("pbanc_sn"))
    if not title or not sn:
        return None
    starts, ends = _day(raw.get("pbanc_rcpt_bgng_dt")), _day(raw.get("pbanc_rcpt_end_dt"))
    target = _clean(raw.get("aply_trgt_ctnt")) or _clean(raw.get("aply_trgt"))
    age = _clean(raw.get("biz_enyy"))
    return {
        "id": f"KS{sn}",
        "title": title,
        "organization": _clean(raw.get("pbanc_ntrp_nm")) or _clean(raw.get("sprv_inst")),
        "category": _clean(raw.get("supt_biz_clsfc")) or "기타",
        "region": _clean(raw.get("supt_regin")) or "전국",
        "deadline_status": deadline_status(ends),
        "starts_on": starts.isoformat() if starts else "",
        "ends_on": ends.isoformat() if ends else "",
        "target": f"{target} ({age})" if target and age else target or age,
        "body": _clean(raw.get("pbanc_ctnt")),
        "detail_url": DETAIL_URL.format(sn=sn),
        "apply_url": _clean(raw.get("aply_mthd_onli_rcpt_istc")) or _clean(raw.get("biz_aply_url")),
        "amount": "",
        "source": "K-Startup",
    }


async def _fetch(key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        for page in range(1, MAX_PAGES + 1):
            resp = await client.get(
                ENDPOINT,
                params={"serviceKey": key, "page": page, "perPage": PAGE_SIZE, "returnType": "json", "cond[rcrt_prgs_yn::EQ]": "Y"},
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("data") or []
            items.extend(p for p in (to_program(r) for r in rows) if p)
            if len(rows) < PAGE_SIZE or len(items) >= int(payload.get("matchCount") or 0):
                break
    # 같은 공고가 두 번 오는 경우를 정리하고 마감이 가까운 순으로
    uniq = {p["id"]: p for p in items}
    return sorted(uniq.values(), key=lambda p: p["ends_on"] or "9999")


async def live_programs() -> Optional[list[dict[str, Any]]]:
    """모집 중 공고 목록 (마감 상태는 오늘 기준). 키가 없거나 처음 받기에 실패하면 None"""
    key = _service_key()
    if not key:
        return None
    fresh = _cache["items"] is not None and time.time() - _cache["at"] < TTL_SEC
    if not fresh:
        async with _lock:
            if _cache["items"] is None or time.time() - _cache["at"] >= TTL_SEC:
                try:
                    _cache["items"] = await _fetch(key)
                    _cache["at"] = time.time()
                    logger.info("[K-Startup] 모집 중 공고 %d건 갱신", len(_cache["items"]))
                except Exception as exc:  # noqa: BLE001 — 실패하면 지난 목록(있으면)이나 샘플로
                    logger.warning("[K-Startup] 공고 받기 실패: %s", exc)
                    _cache["at"] = time.time() - TTL_SEC + 10 * 60  # 10분 뒤 다시 시도
    items = _cache["items"]
    if items is None:
        return None
    today = date.today()
    return [{**p, "deadline_status": deadline_status(_day(p["ends_on"].replace("-", "")), today)} for p in items]

"""
아이템 관련 최신 뉴스 API (로그인 홈 화면용)
키 없이 쓸 수 있는 Google 뉴스 RSS(한국어)를 검색어로 조회해 제목·출처·날짜·링크만 돌려준다.
같은 검색어는 30분 동안 메모리에 캐시한다.
"""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/news")

RSS = "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
CACHE_TTL = 30 * 60
_cache: dict[str, tuple[float, list["NewsItem"]]] = {}


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: str  # ISO 8601, 모르면 ""


class NewsResponse(BaseModel):
    query: str
    items: list[NewsItem]


def _parse(xml_text: str, limit: int) -> list[NewsItem]:
    # RSS에는 DOCTYPE이 없다 — 있으면 엔티티 폭탄(XXE·billion laughs) 가능성이 있어 파싱하지 않는다
    if "<!DOCTYPE" in xml_text[:2000].upper() or "<!ENTITY" in xml_text.upper():
        raise ValueError("DOCTYPE/ENTITY가 든 응답은 처리하지 않음")
    items: list[NewsItem] = []
    for node in ET.fromstring(xml_text).iter("item"):
        title = (node.findtext("title") or "").strip()
        source = (node.findtext("source") or "").strip()
        # 제목 끝의 " - 언론사"는 출처 칸과 겹치므로 뗀다
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        try:
            published = parsedate_to_datetime(node.findtext("pubDate") or "").isoformat()
        except (TypeError, ValueError):
            published = ""
        if title:
            items.append(NewsItem(title=title, source=source, url=(node.findtext("link") or "").strip(), published_at=published))
        if len(items) >= limit:
            break
    return items


@router.get("", response_model=NewsResponse)
async def search_news(
    q: str = Query(min_length=1, max_length=100, description="검색어 (예: 아이템 분야·이름)"),
    limit: int = Query(5, ge=1, le=20),
) -> NewsResponse:
    key = q.strip()
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return NewsResponse(query=key, items=hit[1][:limit])
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(RSS.format(q=quote(key)))
            resp.raise_for_status()
        items = _parse(resp.text, 20)
    except Exception as exc:  # noqa: BLE001 — 뉴스는 부가 정보라 실패해도 빈 목록으로 둔다
        logger.warning("[news] 조회 실패 q=%r: %s", key, exc)
        return NewsResponse(query=key, items=[])
    _cache[key] = (time.time(), items)
    return NewsResponse(query=key, items=items[:limit])

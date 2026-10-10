"""
외부 API 기반 Evidence Retriever

- Naver News Search  : 산업·경쟁사 뉴스 수집
- KOSIS (통계청)     : 시장 통계 수집
- KIPRIS (특허정보)  : 기술/특허 동향 수집

각 API 호출 실패는 경고 로그만 남기고 빈 리스트를 반환한다.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from html import unescape
from typing import Optional
import re

import httpx

from app.core.schemas import Evidence

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0  # 초


def _strip_html(text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", text)).strip()


# ── Naver DataLab Search Trend ───────────────────────────────────────────────

async def _fetch_naver_datalab(
    query: str,
    client_id: str,
    client_secret: str,
) -> list[Evidence]:
    """DataLab Search Trend API — 최근 1년 월별 검색 트렌드를 Evidence로 반환한다."""
    from datetime import date, timedelta

    today = date.today()
    start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }
    body = {
        "startDate": start,
        "endDate": end,
        "timeUnit": "month",
        "keywordGroups": [{"groupName": query, "keywords": [query]}],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("[Naver DataLab] 트렌드 검색 실패 query=%r: %s", query, exc)
        return []

    results_raw = data.get("results", [])
    if not results_raw:
        return []

    periods = results_raw[0].get("data", [])
    if not periods:
        return []

    # 최근 3개월 평균 검색 비율로 요약
    recent = periods[-3:]
    avg_ratio = sum(p.get("ratio", 0) for p in recent) / max(len(recent), 1)
    trend_desc = (
        "검색량 상승 추세" if avg_ratio > 50 else
        "검색량 보통 수준" if avg_ratio > 20 else
        "검색량 낮은 수준"
    )

    return [Evidence(
        title=f"'{query}' 네이버 검색 트렌드",
        source="Naver DataLab",
        url="https://datalab.naver.com/keyword/trendResult.naver",
        content=(
            f"키워드 '{query}'의 최근 3개월 평균 검색 비율: {avg_ratio:.1f}% ({trend_desc}). "
            f"기간: {start} ~ {end}"
        ),
        confidence=0.65,
    )]


# ── KOSIS (통계청) ───────────────────────────────────────────────────────────

async def _fetch_kosis(
    query: str,
    api_key: str,
    num: int = 3,
) -> list[Evidence]:
    url = "https://kosis.kr/openapi/statisticsSearch.do"
    params = {
        "method": "getList",
        "apiKey": api_key,
        "vwCd": "MT_ZTITLE",
        "parentListId": "",
        "searchNm": query,
        "format": "json",
        "jsonVD": "Y",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("[KOSIS] 검색 실패 query=%r: %s", query, exc)
        return []

    if not isinstance(data, list):
        return []

    results: list[Evidence] = []
    for item in data[:num]:
        org = item.get("ORG_NM", "통계청")
        tbl_nm = item.get("TBL_NM", "")
        tbl_id = item.get("TBL_ID", "")
        stat_url = f"https://kosis.kr/statHtml/statHtml.do?orgId={item.get('ORG_ID','')}&tblId={tbl_id}"

        results.append(Evidence(
            title=tbl_nm,
            source=f"KOSIS ({org})",
            url=stat_url,
            content=f"[KOSIS 통계표] {tbl_nm} (기관: {org})",
            confidence=0.75,
        ))
    return results


# ── KIPRIS (특허정보) ────────────────────────────────────────────────────────

async def _fetch_kipris(
    query: str,
    api_key: str,
    num: int = 3,
) -> list[Evidence]:
    url = "https://plus.kipris.or.kr/openapi/rest/PatentAbstractService/wordSearch"
    params = {
        "word": query,
        "accessKey": api_key,
        "format": "json",
        "pageNo": 1,
        "numOfRows": num,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("[KIPRIS] 검색 실패 query=%r: %s", query, exc)
        return []

    try:
        items = (
            data["response"]["body"]["items"]["item"]
        )
        if isinstance(items, dict):
            items = [items]
    except (KeyError, TypeError):
        return []

    results: list[Evidence] = []
    for item in items[:num]:
        app_no = item.get("applicationNumber", "")
        title = item.get("inventionTitle", "")
        applicant = item.get("applicantName", "")
        pub_date_str = item.get("publicationDate", "")

        pub_at: Optional[datetime] = None
        try:
            pub_at = datetime.strptime(pub_date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass

        results.append(Evidence(
            title=title,
            source="KIPRIS (특허)",
            url=f"https://www.kipris.or.kr/khome/simple_view.do?searchType=searchAll&query={app_no}",
            published_at=pub_at,
            content=f"[특허] {title} — 출원인: {applicant}",
            confidence=0.7,
        ))
    return results


# ── 통합 Retriever ───────────────────────────────────────────────────────────

class ExternalEvidenceRetriever:
    """
    Naver뉴스 + KOSIS + KIPRIS 를 병렬로 호출해 Evidence 목록을 반환한다.
    키가 없는 API는 자동으로 건너뛴다.
    """

    def __init__(
        self,
        naver_client_id: str = "",
        naver_client_secret: str = "",
        kosis_api_key: str = "",
        kipris_api_key: str = "",
    ):
        self._naver_id = naver_client_id
        self._naver_secret = naver_client_secret
        self._kosis_key = kosis_api_key
        self._kipris_key = kipris_api_key

    @property
    def is_available(self) -> bool:
        return bool(self._naver_id or self._kosis_key or self._kipris_key)

    async def __call__(self, query: str) -> list[Evidence]:
        tasks = []

        if self._naver_id and self._naver_secret:
            tasks.append(_fetch_naver_datalab(query, self._naver_id, self._naver_secret))
        if self._kosis_key:
            tasks.append(_fetch_kosis(query, self._kosis_key))
        if self._kipris_key:
            tasks.append(_fetch_kipris(query, self._kipris_key))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        evidence: list[Evidence] = []
        for r in results:
            if isinstance(r, list):
                evidence.extend(r)
            else:
                logger.warning("[ExternalRetriever] 오류: %s", r)
        return evidence


def build_external_retriever() -> Optional[ExternalEvidenceRetriever]:
    """settings에서 키를 읽어 ExternalEvidenceRetriever를 생성한다. 키가 없으면 None."""
    from app.core.config import settings

    retriever = ExternalEvidenceRetriever(
        naver_client_id=settings.naver_client_id,
        naver_client_secret=settings.naver_client_secret,
        kosis_api_key=settings.kosis_api_key,
        kipris_api_key=settings.kipris_api_key,
    )
    if not retriever.is_available:
        logger.info("[ExternalRetriever] API 키 없음 — 외부 검색 비활성화")
        return None

    logger.info(
        "[ExternalRetriever] 활성화 — Naver=%s, KOSIS=%s, KIPRIS=%s",
        bool(settings.naver_client_id),
        bool(settings.kosis_api_key),
        bool(settings.kipris_api_key),
    )
    return retriever

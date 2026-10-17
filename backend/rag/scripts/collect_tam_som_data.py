"""
펫테크 TAM/SAM/SOM 보강 데이터 수집 스크립트

1단계: WorldBank 글로벌 경제지표 수집 (TAM 글로벌 컨텍스트)
2단계: KIPRIS 펫테크 특허 검색 (기술 환경 분석)
3단계: 기존 KOSIS/ECOS/NAVER DB에서 핵심 지표 쿼리 후 TAM/SAM/SOM 종합 문서 생성
4단계: rag_corpus 추가 + pinecone_chunks.jsonl 재생성

이 스크립트는 기존 rag_corpus를 수정하지 않고 새 문서를 추가한 뒤 업로드를 갱신합니다.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bizrag.rag_index import RagStore
from bizrag.store import now_iso, stable_hash
from bizrag.pettech import SEOUL, dump
from bizrag.util import to_float
from datetime import datetime, timezone, timedelta

SEOUL_TZ = timezone(timedelta(hours=9))

ENV = {**dotenv_values(ROOT / "new.env"), **{k: v for k, v in os.environ.items() if k.isupper()}}
CORPUS_DB = ROOT / "data/pettech/rag_corpus/knowledge.db"
STATS_DB   = ROOT / "data/pettech/knowledge.db"
CORPUS_DIR = ROOT / "data/pettech/rag_corpus"

WB_NOTE = (
    "World Bank 공개 통계(CC BY 4.0). 반려동물 전용 지출 통계가 아니며, 가계소비에서 "
    "반려동물 비중을 추정하기 위한 경제 규모 지표이다. mrv=15이므로 최근 15년 최신값 기준이다. "
    "값이 없는 연도는 결측이며 0이 아니다. TAM 추정에는 반드시 보정계수(반려동물 지출 비율)를 적용해야 한다."
)
KIPRIS_NOTE = (
    "KIPRIS Plus 검색 결과. 유사 기술 후보 목록이며 특허 침해·독점 여부 판단 근거가 아니다. "
    "출원 건수는 기술 성숙도의 참고치이며 시장 점유율이 아니다. "
    "키워드 기반 검색으로 관련 특허 전체를 포괄하지 않을 수 있다."
)
SYNTHESIS_NOTE = (
    "이 문서는 KOSIS·ECOS·NAVER·WorldBank 수집 데이터를 종합해 TAM/SAM/SOM을 추정한 합성 문서이다. "
    "각 수치의 출처·기간·단위·조사대상을 원 수집 문서에서 확인해야 한다. "
    "추정값은 단순 곱셈 모델이며 실제 시장 규모와 다를 수 있다. "
    "NAVER 지수는 절대 검색량·판매량이 아닌 상대 관심도이다."
)

HTTP = requests.Session()
HTTP.headers["User-Agent"] = "bizrag-tamsom/1.0 (public research)"


def req(url, **kw):
    for attempt in range(3):
        try:
            r = HTTP.get(url, timeout=(10, 55), **kw)
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise RuntimeError(f"network: {type(e).__name__}") from None
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            time.sleep(2 + attempt)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        time.sleep(0.15)
        return r
    raise RuntimeError("max retries exceeded")


def put_doc(db: RagStore, source, doc_type, oid, title, body, url, meta):
    collected = now_iso()
    kst = datetime.fromisoformat(collected).astimezone(SEOUL_TZ).isoformat()
    meta = {
        "domain": "pettech",
        "source": source,
        "collected_at": collected,
        "collected_at_kst": kst,
        "period_start": meta.pop("period_start", "공표값 참조"),
        "period_end": meta.pop("period_end", "공표값 참조"),
        **meta,
    }
    body = f"데이터 기간: {meta['period_start']} ~ {meta['period_end']}\n수집일(KST): {kst}\n" + body
    db.upsert_document(
        source=source,
        doc_type=doc_type,
        original_id=oid,
        title=title,
        body=body,
        url=url,
        license={
            "worldbank": "CC BY 4.0 (World Bank Open Data)",
            "kipris": "KIPRIS Plus 이용약관",
            "synthesis": "bizrag 합성 문서 (원 출처 라이선스 별도 확인)",
        }.get(source, "원 출처 확인"),
        meta=meta,
    )
    db.conn.execute(
        "UPDATE documents SET retrieved_at=? WHERE doc_id=?",
        (meta["collected_at"], f"{source}:{doc_type}:{oid}"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. WorldBank
# ─────────────────────────────────────────────────────────────────────────────

WB_INDICATORS = {
    "SP.POP.TOTL":        "인구 (명)",
    "NY.GDP.MKTP.CD":     "GDP (현재 US$)",
    "NY.GDP.PCAP.CD":     "1인당 GDP (현재 US$)",
    "NE.CON.PRVT.CD":     "가계 최종소비지출 (현재 US$)",
    "IT.NET.USER.ZS":     "인터넷 이용률 (%)",
    "SP.URB.TOTL.IN.ZS":  "도시화율 (%)",
    "SP.POP.65UP.TO.ZS":  "65세 이상 인구 비율 (%)",
    "FP.CPI.TOTL.ZG":     "소비자물가상승률 (%)",
}

# 주요 반려동물 시장 국가 + 비교군
WB_COUNTRIES = ["KOR", "USA", "JPN", "CHN", "DEU", "GBR", "AUS", "FRA", "VNM", "BRA"]

WB_COUNTRY_KO = {
    "KOR": "대한민국",
    "USA": "미국",
    "JPN": "일본",
    "CHN": "중국",
    "DEU": "독일",
    "GBR": "영국",
    "AUS": "호주",
    "FRA": "프랑스",
    "VNM": "베트남",
    "BRA": "브라질",
}


def collect_worldbank(db: RagStore):
    print("[WorldBank] 글로벌 경제지표 수집 시작...", flush=True)
    results = {}
    for ind_code, ind_name in WB_INDICATORS.items():
        url = (
            f"https://api.worldbank.org/v2/country/{';'.join(WB_COUNTRIES)}"
            f"/indicator/{ind_code}"
        )
        try:
            r = req(url, params={"format": "json", "mrv": 15, "per_page": 2000})
            data = r.json()
            if not isinstance(data, list) or len(data) < 2:
                print(f"  ⚠ {ind_code}: 빈 응답", flush=True)
                continue
            rows = data[1] or []
        except Exception as e:
            print(f"  ✗ {ind_code}: {e}", flush=True)
            continue

        # 국가별 최신값 추출
        latest: dict[str, tuple] = {}
        obs = []
        for r in rows:
            iso = r.get("countryiso3code") or (r.get("country") or {}).get("id", "")
            if not iso or r.get("value") is None:
                continue
            val = to_float(r["value"])
            if val is None:
                continue
            period = r["date"]
            obs.append((iso, period, val))
            if iso not in latest or period > latest[iso][0]:
                latest[iso] = (period, val)

        # DB observations 저장
        obs_rows = []
        for iso, period, val in obs:
            obs_rows.append({
                "source": "worldbank",
                "dataset": f"wb:{ind_code}",
                "series_key": iso,
                "query_sig": "tamsom",
                "period": period,
                "value": val,
                "unit": ind_name,
                "dims": {"country": WB_COUNTRY_KO.get(iso, iso), "indicator": ind_name},
            })
        db.upsert_observations(obs_rows)
        db.conn.commit()

        results[ind_code] = {"name": ind_name, "latest": latest, "rows": len(obs)}
        print(f"  ✓ {ind_code} ({ind_name}): {len(obs)}건 저장", flush=True)

    # 지표별 문서 생성
    for ind_code, info in results.items():
        ind_name = info["name"]
        lines = [
            f"WorldBank 글로벌 지표 | {ind_name}",
            f"지표코드: {ind_code} | 조회국가: {', '.join(WB_COUNTRY_KO[c] for c in WB_COUNTRIES if c in info['latest'])}",
            WB_NOTE,
            "",
            "국가별 최신값:",
        ]
        for iso in WB_COUNTRIES:
            if iso in info["latest"]:
                period, val = info["latest"][iso]
                ko = WB_COUNTRY_KO.get(iso, iso)
                lines.append(f"  {ko} ({iso}) {period}: {val:,.2f} {ind_name}")

        put_doc(
            db, "worldbank", "global_indicator", f"{ind_code}:tamsom",
            f"글로벌 경제지표 | {ind_name}",
            "\n".join(lines),
            "https://data.worldbank.org",
            {
                "note": WB_NOTE,
                "indicator_code": ind_code,
                "indicator_name": ind_name,
                "countries": WB_COUNTRIES,
                "period_start": "2009",
                "period_end": "2024",
            },
        )

    # 국가별 통합 문서 생성 (TAM 추정용)
    for iso in WB_COUNTRIES:
        ko = WB_COUNTRY_KO.get(iso, iso)
        lines = [
            f"WorldBank {ko} ({iso}) 종합 경제 프로파일",
            f"TAM 추정을 위한 {ko} 주요 경제지표 (최신값)",
            WB_NOTE,
            "",
        ]
        has_data = False
        for ind_code, info in results.items():
            if iso in info["latest"]:
                period, val = info["latest"][iso]
                lines.append(f"  {info['name']}: {val:,.2f} (기준연도: {period})")
                has_data = True
        if not has_data:
            continue
        # 가계소비 × 반려동물지출비율 추정 (미국 기준 약 1.5%, 한국 약 0.8% 적용)
        gdp_key = "NY.GDP.MKTP.CD"
        cons_key = "NE.CON.PRVT.CD"
        gdp_val = results.get(gdp_key, {}).get("latest", {}).get(iso)
        cons_val = results.get(cons_key, {}).get("latest", {}).get(iso)
        if cons_val:
            period_c = cons_val[0]
            c = cons_val[1]
            pet_ratio_ko = 0.008 if iso == "KOR" else (0.015 if iso in ("USA", "AUS") else 0.010)
            tam_est = c * pet_ratio_ko
            lines += [
                "",
                f"TAM 추정 (가계소비 기반, 반려동물 지출 비율 {pet_ratio_ko*100:.1f}% 적용):",
                f"  가계소비지출 {period_c}: {c:,.0f} US$ × {pet_ratio_ko*100:.1f}% = {tam_est:,.0f} US$ (반려동물 소비 추정)",
                "  주의: 비율은 산업 리포트 추정치를 참조한 보정계수이며 실증 조사값이 아니다.",
            ]
        put_doc(
            db, "worldbank", "country_profile", f"{iso}:tamsom",
            f"글로벌 경제 프로파일 | {ko}",
            "\n".join(lines),
            f"https://data.worldbank.org/country/{iso.lower()}",
            {
                "note": WB_NOTE,
                "country_iso": iso,
                "country_ko": ko,
                "period_start": "2009",
                "period_end": "2024",
            },
        )

    db.conn.commit()
    print(f"[WorldBank] 완료: 지표 {len(results)}개, 국가 {len(WB_COUNTRIES)}개", flush=True)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 2. KIPRIS 특허
# ─────────────────────────────────────────────────────────────────────────────

KIPRIS_SEARCHES = [
    ("반려동물 IoT",       "반려동물IoT"),
    ("펫캠 CCTV",          "펫캠"),
    ("자동급식기",          "자동급식기"),
    ("반려동물 웨어러블",   "웨어러블"),
    ("반려동물 헬스케어",   "헬스케어"),
    ("펫시터 앱",           "펫시터"),
    ("반려동물 행동분석",   "행동분석"),
    ("스마트 사료",         "스마트사료"),
    ("반려동물 원격",       "원격돌봄"),
    ("펫 구독 서비스",      "구독서비스"),
]


def collect_kipris(db: RagStore):
    import urllib.parse
    import xml.etree.ElementTree as ET

    key_raw = ENV.get("KIPRIS_API_KEY", "")
    if not key_raw:
        print("[KIPRIS] API 키 없음, 건너뜀", flush=True)
        return {}

    key = urllib.parse.unquote(key_raw)
    base = "https://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"
    results = {}

    for word, label in KIPRIS_SEARCHES:
        params = {
            "word": word,
            "patent": "true",
            "utility": "true",
            "numOfRows": 30,
            "pageNo": 1,
            "ServiceKey": key,
        }
        try:
            r = req(f"{base}/getWordSearch", params=params, headers={"Accept": "application/xml"})
            root = ET.fromstring(r.content)
        except Exception as e:
            print(f"  ✗ KIPRIS '{word}': {e}", flush=True)
            continue

        total_text = root.findtext(".//totalCount") or "0"
        try:
            total = int(total_text)
        except ValueError:
            total = 0

        items = []
        for it in root.iter("item"):
            def t(tag):
                for c in it:
                    if c.tag.lower() == tag.lower():
                        return (c.text or "").strip() or None
                return None

            d = {
                "app_no": t("applicationNumber"),
                "title": t("inventionTitle"),
                "applicant": t("applicantName"),
                "ipc": t("ipcNumber"),
                "app_date": t("applicationDate"),
                "status": t("registerStatus"),
                "abstract": t("astrtCont"),
            }
            items.append(d)

        by_year: dict[str, int] = {}
        by_applicant: dict[str, int] = {}
        for d in items:
            y = (d["app_date"] or "")[:4]
            if y:
                by_year[y] = by_year.get(y, 0) + 1
            ap = d["applicant"] or "미상"
            by_applicant[ap] = by_applicant.get(ap, 0) + 1

        results[label] = {
            "word": word,
            "total": total,
            "returned": len(items),
            "by_year": by_year,
            "top_applicants": sorted(by_applicant.items(), key=lambda x: -x[1])[:5],
        }

        lines = [
            f"KIPRIS 펫테크 특허 검색 | 키워드: {word}",
            f"전체 검색 건수: {total}건 (반환 {len(items)}건)",
            KIPRIS_NOTE,
            "",
            f"연도별 출원 추이: {json.dumps(dict(sorted(by_year.items())), ensure_ascii=False)}",
            f"상위 출원인: {json.dumps([f'{a}({n})' for a,n in results[label]['top_applicants']], ensure_ascii=False)}",
            "",
            "상위 특허 목록:",
        ]
        for d in items[:15]:
            lines.append(
                f"  [{d['app_date'] or '?'}] {d['title'] or '제목없음'} | 출원인: {d['applicant'] or '?'} | "
                f"IPC: {d['ipc'] or '?'} | 상태: {d['status'] or '?'}"
            )

        put_doc(
            db, "kipris", "patent_search", f"{label}:tamsom",
            f"펫테크 특허 현황 | {word}",
            "\n".join(lines),
            "https://www.kipris.or.kr",
            {
                "note": KIPRIS_NOTE,
                "search_word": word,
                "total_count": total,
                "returned_count": len(items),
                "by_year": by_year,
                "period_start": min(by_year, default="미상"),
                "period_end": max(by_year, default="미상"),
            },
        )
        db.conn.commit()
        print(f"  ✓ KIPRIS '{word}': 총 {total}건 (반환 {len(items)}건)", flush=True)

    print(f"[KIPRIS] 완료: 검색어 {len(results)}개", flush=True)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 3. TAM / SAM / SOM 종합 문서
# ─────────────────────────────────────────────────────────────────────────────

def collect_synthesis(db: RagStore, wb_results: dict, kipris_results: dict):
    """기존 KOSIS/ECOS/NAVER + WorldBank 데이터를 종합해 TAM/SAM/SOM 문서를 생성한다."""
    import sqlite3

    stats = sqlite3.connect(f"file:{STATS_DB.as_posix()}?mode=ro", uri=True)
    stats.row_factory = sqlite3.Row

    def q(sql, params=()):
        return [dict(r) for r in stats.execute(sql, params)]

    # ── KOSIS 핵심 지표 ──────────────────────────────────────────────────
    kosis_obs = q(
        "SELECT series_key, value, unit FROM observations "
        "WHERE source='kosis' AND period='2025' AND value IS NOT NULL "
        "ORDER BY dataset, series_key"
    )

    # 양육가구 비율 추출 (C1=01: 전체, '반려동물 양육 여부')
    ownership_rows = q(
        "SELECT series_key, value, unit FROM observations "
        "WHERE source='kosis' AND period='2025' "
        "  AND dataset LIKE 'kosis:114/%' "
        "  AND series_key LIKE '%양육 여부%' "
        "  AND value IS NOT NULL"
    )

    # 월평균 양육비용 추출
    cost_rows = q(
        "SELECT series_key, value, unit FROM observations "
        "WHERE source='kosis' AND period='2025' "
        "  AND dataset LIKE 'kosis:114/%' "
        "  AND series_key LIKE '%양육비용%' "
        "  AND value IS NOT NULL"
    )

    # ECOS 최신 소비자물가지수
    ecos_rows = q(
        "SELECT series_key, period, value, unit "
        "FROM observations WHERE source='ecos' "
        "ORDER BY period DESC LIMIT 8"
    )

    # NAVER 쇼핑 최근 12개월 평균 (segment=전체 기준)
    naver_shopping = q(
        "SELECT series_key, AVG(value) avg_v "
        "FROM observations WHERE source='naver' "
        "  AND dataset='pet_shopping_keyword' "
        "  AND query_sig IN ("
        "    SELECT DISTINCT query_sig FROM observations "
        "    WHERE source='naver' AND dataset='pet_shopping_keyword' "
        "    ORDER BY period DESC LIMIT 12"
        "  ) "
        "GROUP BY series_key ORDER BY avg_v DESC LIMIT 20"
    )

    stats.close()

    # ── 한국 가계 규모 (WorldBank KOR) ──────────────────────────────────
    kor_cons = None
    kor_pop = None
    kor_gdp = None
    if wb_results:
        kor_cons = wb_results.get("NE.CON.PRVT.CD", {}).get("latest", {}).get("KOR")
        kor_pop  = wb_results.get("SP.POP.TOTL", {}).get("latest", {}).get("KOR")
        kor_gdp  = wb_results.get("NY.GDP.MKTP.CD", {}).get("latest", {}).get("KOR")

    # ── TAM 문서 ─────────────────────────────────────────────────────────
    tam_lines = [
        "펫테크 TAM (총 시장 규모) 추정",
        SYNTHESIS_NOTE,
        "",
        "## 글로벌 반려동물 시장 TAM 추정",
        "",
        "반려동물 시장 규모는 공식 집계 통계가 없어 아래 방법론으로 추정한다:",
        "  방법 1) 주요국 가계소비지출 × 반려동물 지출 비율 합산",
        "  방법 2) 한국 시장 규모 × GDP 역산 (한국 글로벌 반려동물 시장 점유율 추정)",
        "",
        "### 주요국 WorldBank 가계소비지출 기반 반려동물 시장 추정",
    ]

    total_tam_usd = 0.0
    for iso in ["USA", "CHN", "DEU", "GBR", "JPN", "FRA", "AUS", "KOR", "BRA"]:
        if not wb_results:
            break
        cons_info = wb_results.get("NE.CON.PRVT.CD", {}).get("latest", {}).get(iso)
        if not cons_info:
            continue
        period_c, c = cons_info
        ratio = {
            "USA": 0.015, "AUS": 0.015, "GBR": 0.012, "DEU": 0.010,
            "FRA": 0.010, "JPN": 0.008, "KOR": 0.008, "CHN": 0.005, "BRA": 0.005
        }.get(iso, 0.008)
        est = c * ratio
        total_tam_usd += est
        ko = WB_COUNTRY_KO.get(iso, iso)
        tam_lines.append(
            f"  {ko}: 가계소비 {c:,.0f}억$ (WorldBank {period_c}) × {ratio*100:.1f}% = {est:,.0f}억$ 반려동물 시장 추정"
        )

    if total_tam_usd > 0:
        tam_lines += [
            "",
            f"주요 9개국 합산 TAM 추정: {total_tam_usd:,.0f} US$ (글로벌 시장의 약 80~85% 커버)",
            f"전세계 TAM 추정: {total_tam_usd / 0.82:,.0f} US$ (주요국 점유율 82% 가정)",
            "",
            "※ 반려동물 지출 비율은 APPA·Euromonitor 등 산업 리포트 추정치 기반 보정계수이며 실측값이 아니다.",
            "※ 펫테크(IoT·구독·헬스케어·웨어러블) 비중 추가 적용 필요 (전체 반려동물 시장 대비 약 10~20% 추정).",
        ]

    tam_lines += [
        "",
        "### 한국 글로벌 점유율 역산",
    ]
    if kor_gdp and wb_results.get("NY.GDP.MKTP.CD", {}).get("latest", {}).get("USA"):
        usa_gdp = wb_results["NY.GDP.MKTP.CD"]["latest"]["USA"][1]
        kor_share = kor_gdp[1] / usa_gdp * 100
        tam_lines.append(f"  한국 GDP: {kor_gdp[1]:,.0f} US$ / 미국 GDP: {usa_gdp:,.0f} US$ = 점유율 {kor_share:.2f}%")

    tam_lines += [
        "",
        "### ECOS 반려동물 소비자물가지수 추이 (시장 가격 성장률 참고)",
    ]
    for r in ecos_rows[:4]:
        tam_lines.append(f"  {r['series_key']} {r['period']}: {r['value']} {r['unit']}")

    put_doc(
        db, "synthesis", "tam_analysis", "pettech:tam:v1",
        "펫테크 TAM 분석 | 글로벌 총 시장 규모 추정",
        "\n".join(tam_lines),
        "https://data.worldbank.org",
        {
            "note": SYNTHESIS_NOTE,
            "period_start": "2020",
            "period_end": "2025",
            "methodology": "WorldBank 가계소비 × 반려동물 지출 비율 추정",
        },
    )

    # ── SAM 문서 ─────────────────────────────────────────────────────────
    sam_lines = [
        "펫테크 SAM (유효 시장 규모) 추정 | 대한민국",
        SYNTHESIS_NOTE,
        "",
        "## 한국 반려동물 서비스 유효시장 (SAM)",
        "",
        "SAM = 국내 반려동물 양육가구 수 × 서비스 카테고리별 평균 지출액",
        "",
        "### KOSIS 2025년 반려동물양육현황조사 핵심 지표",
    ]
    if ownership_rows:
        for r in ownership_rows[:5]:
            sam_lines.append(f"  {r['series_key']}: {r['value']} {r['unit'] or ''}")
    else:
        sam_lines.append("  (양육 여부 세부 지표는 원 DB 조회 필요)")

    sam_lines += [
        "",
        "### 월평균 양육비용 (KOSIS 2025)",
    ]
    if cost_rows:
        for r in cost_rows[:5]:
            sam_lines.append(f"  {r['series_key']}: {r['value']} {r['unit'] or ''}")
    else:
        sam_lines.append("  (비용 세부 지표는 원 DB 조회 필요)")

    sam_lines += [
        "",
        "### SAM 추정 (가구 수 × 월 지출 × 12)",
        "  주의: 양육가구 수는 KOSIS 표본조사 비율에서 역산하며, 역산 시 모집단(전국 가구 수)과 표집 오차를 함께 고려해야 한다.",
        "  주의: 펫테크 SAM은 전체 반려동물 지출 중 기술 서비스(IoT·헬스케어·구독) 비중을 추가 적용해야 한다.",
        "",
        "### NAVER 쇼핑 인사이트 기반 SAM 세그먼트 상대 크기 (최근 12개월 평균 클릭 지수)",
    ]
    for r in naver_shopping[:10]:
        sam_lines.append(f"  {r['series_key']}: 쇼핑 클릭 지수 {r['avg_v']:.1f} (요청 내 상대지수, 비교 기준 동일)")

    sam_lines += [
        "",
        "### ECOS 반려동물 물가 추이 (가격 성장성)",
    ]
    for r in ecos_rows[:4]:
        sam_lines.append(f"  {r['series_key']} {r['period']}: {r['value']} {r['unit']}")

    put_doc(
        db, "synthesis", "sam_analysis", "pettech:sam:v1",
        "펫테크 SAM 분석 | 한국 유효 시장 규모 추정",
        "\n".join(sam_lines),
        "https://kosis.kr",
        {
            "note": SYNTHESIS_NOTE,
            "period_start": "2025",
            "period_end": "2025",
            "methodology": "KOSIS 양육가구 × 평균 지출 + NAVER 쇼핑 세그먼트",
        },
    )

    # ── SOM 문서 ─────────────────────────────────────────────────────────
    som_lines = [
        "펫테크 SOM (점유 가능 시장) 추정 | 주요 서비스 세그먼트",
        SYNTHESIS_NOTE,
        "",
        "## SOM 추정 근거",
        "",
        "SOM = SAM × 서비스 세그먼트 NAVER 관심도 비율 × 경쟁 강도 보정",
        "",
        "### 세그먼트별 NAVER 검색 관심도 추이 (펫가드·구독박스·홈헬스케어 비교)",
    ]

    # 사업영역비교 batch에서 관심도 추출
    seg_rows = q(
        "SELECT series_key, AVG(value) avg_v "
        "FROM observations WHERE source='naver' "
        "  AND dataset='pet_search_trend' "
        "  AND dims_json LIKE '%사업영역비교%' "
        "GROUP BY series_key ORDER BY avg_v DESC"
    ) if False else []  # placeholder - will be computed below

    import sqlite3 as _sqlite3
    stats2 = _sqlite3.connect(f"file:{STATS_DB.as_posix()}?mode=ro", uri=True)
    stats2.row_factory = _sqlite3.Row
    seg_rows = [dict(r) for r in stats2.execute(
        "SELECT series_key, AVG(value) avg_v "
        "FROM observations WHERE source='naver' "
        "  AND dataset='pet_search_trend' "
        "  AND dims_json LIKE '%사업영역비교%' "
        "GROUP BY series_key ORDER BY avg_v DESC"
    )]
    stats2.close()

    if seg_rows:
        total_interest = sum(r["avg_v"] for r in seg_rows) or 1
        for r in seg_rows:
            share = r["avg_v"] / total_interest * 100
            som_lines.append(
                f"  {r['series_key']}: 평균 관심도 {r['avg_v']:.1f} (비중 {share:.1f}%) — "
                f"NAVER 검색 관심도 기준 세그먼트 상대 크기"
            )
    else:
        som_lines.append("  (세그먼트별 NAVER 관심도는 원 DB에서 사업영역비교 배치 조회)")

    som_lines += [
        "",
        "### 펫테크 KIPRIS 특허 기술 성숙도 (경쟁 강도 참고)",
    ]
    for label, info in kipris_results.items():
        total = info.get("total", 0)
        word = info.get("word", label)
        recent = sum(v for k, v in info.get("by_year", {}).items() if k >= "2020")
        som_lines.append(
            f"  {word}: 누적 특허 {total}건, 2020년 이후 {recent}건 — "
            f"{'성숙 기술 (경쟁 높음)' if total > 100 else '초기·성장 기술'}"
        )

    som_lines += [
        "",
        "### 지역별 인프라 분포 (파트너십·채널 접근성)",
        "  동물병원·동물미용업·동물약국 지역별 분포 → 서비스 접근 가능 지역 범위",
        "  세부 지역별 수치는 'local_csv:infrastructure_region' 문서 참조",
        "",
        "### SOM 단계별 추정 방법",
        "  1단계: SAM × 세그먼트 관심도 비율 = 세그먼트별 SAM",
        "  2단계: 세그먼트 SAM × 진입 가능성(특허 공백, 경쟁사 점유율 100%-α) = SOM 상한",
        "  3단계: SOM 상한 × 도달 가능 채널 가중치 = 현실적 SOM",
        "  주의: NAVER 지수는 절대값이 아니므로 비율만 사용하며 정규화 후 적용한다.",
    ]

    put_doc(
        db, "synthesis", "som_analysis", "pettech:som:v1",
        "펫테크 SOM 분석 | 점유 가능 시장 추정",
        "\n".join(som_lines),
        "https://kosis.kr",
        {
            "note": SYNTHESIS_NOTE,
            "period_start": "2023",
            "period_end": "2026",
            "methodology": "NAVER 관심도 비율 + KIPRIS 특허 경쟁 강도 + 인프라 분포",
        },
    )

    # ── 방법론 가이드 문서 ───────────────────────────────────────────────
    guide_lines = [
        "펫테크 TAM/SAM/SOM 추정 방법론 및 데이터 소스 가이드",
        "",
        "## 데이터 소스별 역할",
        "",
        "| 출처 | 역할 | TAM/SAM/SOM |",
        "|---|---|---|",
        "| KOSIS 반려동물양육현황조사 (2025) | 국내 양육가구 비율, 평균 지출, 양육 마리수 | SAM 핵심 |",
        "| ECOS 소비자물가지수 (반려동물용품·관리비) | 시장 가격 성장률 | TAM/SAM 성장률 |",
        "| NAVER 검색·쇼핑 인사이트 | 세그먼트별 상대적 관심도 | SOM 세그먼트 비율 |",
        "| WorldBank (GDP·가계소비·인구) | 글로벌 경제 규모 기반 TAM 추정 | TAM 글로벌 |",
        "| KIPRIS 특허 | 기술 성숙도, 경쟁 강도 | SOM 보정 |",
        "| 동물병원·미용업·약국 인허가 CSV | 서비스 채널 인프라 | SOM 채널 |",
        "| 연구논문 (PDF) | 구매의도·만족도·구독행동 근거 | SAM/SOM 근거 |",
        "",
        "## TAM 추정 공식",
        "글로벌 TAM = Σ(국가별 가계소비 × 반려동물 지출 비율)",
        "  - 반려동물 지출 비율: 미국·호주 1.5%, 영국·독일·프랑스 1.0~1.2%, 한국·일본 0.8%, 중국·브라질 0.5%",
        "  - 출처: APPA(미국반려동물제품협회), Euromonitor 추정치 기반 보정계수 (실측값 아님)",
        "",
        "## SAM 추정 공식",
        "한국 SAM = 반려동물 양육가구 수 × 월평균 지출 × 12",
        "  - 양육가구 수: KOSIS 조사 양육 비율 × 통계청 가구 수 (역산)",
        "  - 펫테크 SAM = 전체 반려동물 SAM × 기술 서비스 침투율",
        "",
        "## SOM 추정 공식",
        "SOM = SAM × 세그먼트 비중(NAVER) × 경쟁 진입 가능성",
        "  - 세그먼트 비중: NAVER 쇼핑 클릭 지수 정규화 비율",
        "  - 경쟁 진입 가능성: 1 - 기존 플레이어 점유율 (시장 조사 필요)",
        "",
        "## 주의사항",
        "- KOSIS 표본조사: 전국 반려가구 총수가 아닌 표본에서의 비율이므로 역산 시 신뢰구간 고려 필요",
        "- NAVER 지수: 동일 요청 내 최대=100 상대지수이며 서로 다른 요청(query_sig)간 비교 불가",
        "- WorldBank 비율: 산업 리포트 기반 추정치, 공식 통계 아님",
        "- ECOS: 소비자물가지수(2020=100)는 가격 상대지표이며 매출액이 아님",
    ]

    put_doc(
        db, "synthesis", "methodology_guide", "pettech:methodology:v1",
        "펫테크 TAM/SAM/SOM 방법론 가이드",
        "\n".join(guide_lines),
        "https://kosis.kr",
        {
            "note": SYNTHESIS_NOTE,
            "period_start": "2020",
            "period_end": "2026",
            "methodology": "다중 출처 통합 방법론",
        },
    )

    db.conn.commit()
    print("[종합 문서] TAM/SAM/SOM 문서 4건 생성 완료", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. 메인
# ─────────────────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("펫테크 TAM/SAM/SOM 데이터 수집 시작")
    print("=" * 60)

    db = RagStore(CORPUS_DB)
    try:
        # 1. WorldBank
        wb_results = collect_worldbank(db)

        # 2. KIPRIS
        kipris_results = collect_kipris(db)

        # 3. 종합 문서
        collect_synthesis(db, wb_results, kipris_results)

        # 4. reindex all new docs
        print("[reindex] 새 문서 재색인 중...", flush=True)
        reindexed = 0
        for (doc_id,) in db.conn.execute("SELECT doc_id FROM documents").fetchall():
            reindexed += db.reindex(doc_id)
        db.conn.commit()
        print(f"[reindex] {reindexed}건 재색인", flush=True)

        # 5. pinecone_chunks.jsonl 재생성
        print("[export] pinecone_chunks.jsonl 재생성 중...", flush=True)
        export_dir = CORPUS_DIR / "exports"
        result = db.export_vectors(export_dir)
        print(f"[export] {result['chunks']}청크 → pinecone_chunks.jsonl", flush=True)

        # 집계
        docs = db.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = db.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        obs = db.conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        print()
        print(f"✓ 문서: {docs}개 | 청크: {chunks}개 | 관측값: {obs}개")

    finally:
        db.close()
        HTTP.close()


if __name__ == "__main__":
    raise SystemExit(main())

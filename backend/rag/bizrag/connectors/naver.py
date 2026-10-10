"""네이버 검색어 트렌드·쇼핑인사이트 (NAVER API HUB, 네이버 클라우드).

- 2026년 네이버 개발자센터 오픈API(openapi.naver.com)가 NAVER API HUB로 이관되었다.
  호스트·인증 헤더·경로가 모두 바뀌었고, 키는 NCP 콘솔 > NAVER API HUB에서 앱을 등록해 받는다.
  (쇼핑 검색 API는 이관 대상이 아니어서 제공되지 않는다.)
- 데이터랩 지수는 '조회 조건 안에서 최댓값=100'인 상대값이다.
  그래서 요청 전체를 해시한 query_sig를 같이 저장하고, 같은 sig끼리만 비교하게 한다.
- 키워드가 있어야 호출할 수 있으므로 검색어 트렌드/쇼핑 키워드는 on-demand(+캐시)로,
  쇼핑 분야(카테고리) 추이와 연령·성별 분포는 월 1회 정기 수집으로 둔다.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..store import stable_hash
from ..util import months_ago
from .base import ApiError, Connector, Job, status_to_kind

API = "https://naverapihub.apigw.ntruss.com"
SEARCH_TREND = "/search-trend/v1/search"
SHOP_CATEGORIES = "/shopping/v1/categories"
SHOP_CATEGORY = "/shopping/v1/category/"  # + keywords | age | gender

# 네이버 쇼핑 1분류 카테고리 코드
DEFAULT_CATEGORIES = {
    "패션의류": "50000000", "패션잡화": "50000001", "화장품/미용": "50000002",
    "디지털/가전": "50000003", "가구/인테리어": "50000004", "출산/육아": "50000005",
    "식품": "50000006", "스포츠/레저": "50000007", "생활/건강": "50000008",
    "여가/생활편의": "50000009",
}


class Naver(Connector):
    name = "naver"
    title = "네이버 검색어트렌드·쇼핑인사이트"
    key_envs = ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET")
    signup_url = ("https://console.ncloud.com > NAVER API HUB (이용 신청 → 앱 등록 → API: 검색어 트렌드, 쇼핑인사이트 "
                  "→ 앱의 Client ID/Secret을 .env에 입력)")
    license = "NAVER API HUB 이용약관"

    # ------------------------------------------------------------ http
    def _headers(self) -> dict:
        return {
            "X-NCP-APIGW-API-KEY-ID": self.key("NAVER_CLIENT_ID"),
            "X-NCP-APIGW-API-KEY": self.key("NAVER_CLIENT_SECRET"),
            "Content-Type": "application/json",
        }

    def _call(self, method: str, path: str, **kw) -> dict:
        resp = self.http.request(method, API + path, headers=self._headers(), **kw)
        if resp.status_code == 200:
            return resp.json()
        try:
            err = resp.json()
        except ValueError:
            err = {"errMsg": resp.text[:200]}
        # API Gateway 오류는 {"error": {errorCode, message}}, 트렌드·쇼핑인사이트 오류는 {errMsg, errId}
        gw = err.get("error") if isinstance(err.get("error"), dict) else {}
        code = gw.get("errorCode") or err.get("errorCode") or ""
        text = gw.get("message") or err.get("errMsg") or err.get("errorMessage") or ""
        msg = f"{resp.status_code} {code} {text}".strip()
        kind = status_to_kind(resp.status_code)
        hint = ""
        if resp.status_code == 401:
            hint = ("NCP 콘솔 > NAVER API HUB에서 받은 앱의 Client ID/Secret인지, 그 앱에 "
                    f"'{'검색어 트렌드' if path == SEARCH_TREND else '쇼핑인사이트'}' 이용 신청이 되어 있는지 확인")
        elif resp.status_code == 403:
            hint = "NAVER API HUB 앱의 API 권한 설정 확인"
        elif resp.status_code == 429:
            hint = "호출 한도 초과 — NCP 콘솔에서 사용량 확인"
        elif resp.status_code in (300, 404):
            hint = f"API 경로 확인 ({path})"
        raise ApiError(kind, msg, hint)

    # ----------------------------------------------------------- check
    def _check(self) -> str:
        end = date.today().replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        body = {
            "startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "month",
            "keywordGroups": [{"groupName": "점검", "keywords": ["창업"]}],
        }
        self._call("POST", SEARCH_TREND, json=body)
        try:
            self._call("POST", SHOP_CATEGORIES, json={
                "startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "month",
                "category": [{"name": "식품", "param": ["50000006"]}],
            })
        except ApiError as e:
            raise ApiError(e.kind, "검색어트렌드는 OK, 쇼핑인사이트 실패: " + e.message, e.hint)
        return "검색어트렌드 OK, 쇼핑인사이트 OK"

    # --------------------------------------------- on-demand: 검색어 트렌드
    def search_trend(
        self,
        keyword_groups: dict[str, list[str]],
        months: int = 36,
        time_unit: str = "month",
        device: str = "",
        gender: str = "",
        ages: list[str] | None = None,
    ) -> dict:
        """키워드 그룹별 검색 관심도(상대지수). 최대 5그룹, 그룹당 20키워드."""
        if not keyword_groups or len(keyword_groups) > 5:
            raise ApiError("input", "키워드 그룹은 1~5개")
        end = _end_date(time_unit)
        start = months_ago(months)
        body = {
            "startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": time_unit,
            "keywordGroups": [
                {"groupName": g, "keywords": list(dict.fromkeys(kws))[:20] or [g]}
                for g, kws in keyword_groups.items()
            ],
        }
        if device:
            body["device"] = device
        if gender:
            body["gender"] = gender
        if ages:
            body["ages"] = ages
        return self.cached("naver_search_trend", body, 24 * 7, lambda: self._search_trend(body))

    def _search_trend(self, body: dict) -> dict:
        data = self._call("POST", SEARCH_TREND, json=body)
        sig = stable_hash(body)[:12]
        rows, series = [], {}
        for res in data.get("results", []):
            g = res.get("title")
            pts = [(p["period"], p.get("ratio")) for p in res.get("data", [])]
            series[g] = pts
            rows += [{
                "source": "naver", "dataset": "datalab_search", "series_key": g,
                "query_sig": sig, "period": p, "value": v, "unit": "상대지수(조회조건 내 최대=100)",
                "dims": {"keywords": res.get("keywords"), "filters": {
                    k: body.get(k) for k in ("device", "gender", "ages") if body.get(k)}},
            } for p, v in pts]
        self.store.upsert_observations(rows)
        return {"query_sig": sig, "period": [body["startDate"], body["endDate"]],
                "time_unit": body["timeUnit"], "series": series,
                "summary": _trend_summary(series),
                "note": "상대지수: 같은 query_sig 안에서만 비교 가능, 절대 검색량 아님"}

    # ------------------------------------------ on-demand: 쇼핑 키워드 클릭
    def shopping_keyword_trend(self, category_id: str, keywords: list[str], months: int = 36) -> dict:
        """쇼핑 분야 안에서 키워드별 클릭 추이 (최대 5개)."""
        end = _end_date("month")
        body = {
            "startDate": months_ago(months).isoformat(), "endDate": end.isoformat(),
            "timeUnit": "month", "category": str(category_id),
            "keyword": [{"name": k, "param": [k]} for k in keywords[:5]],
        }
        return self.cached("naver_shop_kw", body, 24 * 7, lambda: self._shop_kw(body))

    def _shop_kw(self, body: dict) -> dict:
        data = self._call("POST", SHOP_CATEGORY + "keywords", json=body)
        sig = stable_hash(body)[:12]
        series, rows = {}, []
        for res in data.get("results", []):
            g = res.get("title")
            pts = [(p["period"], p.get("ratio")) for p in res.get("data", [])]
            series[g] = pts
            rows += [{"source": "naver", "dataset": f"shop_kw:{body['category']}", "series_key": g,
                      "query_sig": sig, "period": p, "value": v, "unit": "상대지수(클릭)"} for p, v in pts]
        self.store.upsert_observations(rows)
        return {"query_sig": sig, "category": body["category"], "series": series,
                "summary": _trend_summary(series)}

    # -------------------------------------------------- 정기: 쇼핑 분야 추이
    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        return [Job(self.name, "shopping_categories", self.cfg.get("cadence", "monthly"),
                    self.sync_categories, "쇼핑 1분류 클릭 추이 + 분야별 연령·성별 분포")]

    def sync_categories(self) -> int:
        cats: dict = self.cfg.get("shopping_categories") or DEFAULT_CATEGORIES
        end = date.today().replace(day=1) - timedelta(days=1)
        start = months_ago(int(self.cfg.get("history_months", 36)))
        n = 0
        names = list(cats.items())
        # 같은 요청 안에서만 비교 가능하므로, 기준 분야(첫 번째)를 모든 묶음에 포함해 상대비교 가능하게 한다
        anchor = names[0]
        for i in range(1, len(names), 2):
            group = [anchor] + names[i : i + 2]
            body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "month",
                    "category": [{"name": nm, "param": [cid]} for nm, cid in group]}
            data = self._call("POST", SHOP_CATEGORIES, json=body)
            sig = "anchor:" + anchor[1] + ":" + stable_hash(body)[:8]
            for res in data.get("results", []):
                n += self.store.upsert_observations({
                    "source": "naver", "dataset": "shop_category", "series_key": res.get("title"),
                    "query_sig": sig, "period": p["period"], "value": p.get("ratio"),
                    "unit": "상대지수(클릭)", "dims": {"anchor": anchor[0]},
                } for p in res.get("data", []))
        # 분야별 연령/성별 분포 (최근 12개월)
        s12 = months_ago(12).isoformat()
        for nm, cid in names:
            for kind in ("age", "gender"):
                body = {"startDate": s12, "endDate": end.isoformat(), "timeUnit": "month", "category": cid}
                data = self._call("POST", SHOP_CATEGORY + kind, json=body)
                sig = stable_hash(body)[:12]
                for res in data.get("results", []):
                    n += self.store.upsert_observations({
                        "source": "naver", "dataset": f"shop_category_{kind}", "series_key": f"{nm}|{p.get('group')}",
                        "query_sig": sig, "period": p["period"], "value": p.get("ratio"),
                        "unit": "상대지수(클릭)",
                    } for p in res.get("data", []))
        self.store.conn.commit()
        return n


def _end_date(time_unit: str) -> date:
    """월 단위면 지난달 말일까지 (이번 달 일부만 들어간 구간이 최근값·증감률을 왜곡하지 않게), 그 외는 어제까지."""
    today = date.today()
    if time_unit == "month":
        return today.replace(day=1) - timedelta(days=1)
    return today - timedelta(days=1)


def _trend_summary(series: dict[str, list]) -> dict:
    """최근 12개 시점 평균 vs 직전 12개 시점 평균 변화율, 최근값, 최고점 시점."""
    out = {}
    for g, pts in series.items():
        vals = [v for _, v in pts if v is not None]
        if not vals:
            continue
        recent, prev = vals[-12:], vals[-24:-12]
        s = {"latest": vals[-1], "peak_period": max(pts, key=lambda x: x[1] or 0)[0],
             "recent_avg": round(sum(recent) / len(recent), 2)}
        if prev:
            pa = sum(prev) / len(prev)
            s["yoy_change_pct"] = round((s["recent_avg"] - pa) / pa * 100, 1) if pa else None
        out[g] = s
    return out

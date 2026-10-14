"""KOSIS 국가통계포털.

- 월 1회: (1) 감시 검색어로 통계표 목록을 찾아 '통계표 카탈로그' 문서로 저장
          → 에이전트가 문서검색으로 어떤 통계표가 있는지 찾을 수 있음
         (2) 감시 통계표 + 에이전트가 한 번이라도 조회했던 통계표를 최신값으로 갱신
- 검색 시: find_tables(검색어), fetch_table(orgId, tblId) — 결과는 DB에 쌓인다.
"""
from __future__ import annotations

import json
import re

from ..util import to_float
from .base import ApiError, Connector, Job

BASE = "https://kosis.kr/openapi"
ERR = {
    "10": ("auth", "인증키 누락"), "11": ("auth", "인증키 기간만료"),
    "20": ("input", "필수요청변수 누락"), "21": ("input", "잘못된 요청변수"),
    "30": ("no_data", "조회결과 없음"), "31": ("input", "조회결과 초과(4만 셀) — 기간/분류를 줄이세요"),
    "40": ("quota", "호출가능건수 제한"), "41": ("quota", "호출가능ROW수 제한"),
    "42": ("quota", "사용자별 이용 제한"), "50": ("server", "서버오류"),
}
PRD_PROBE = ["Y", "M", "Q", "H", "F", "IR"]
# 메타(getMeta type=PRD)의 수록주기 이름 → prdSe 코드. "2년", "5년" 같은 다년 주기는 F
PRD_CODE = {"일": "D", "월": "M", "분기": "Q", "반기": "H", "반년": "H", "년": "Y", "부정기": "IR"}


def prd_code(name: str) -> str:
    name = (name or "").strip()
    if name in PRD_CODE:
        return PRD_CODE[name]
    return "F" if re.fullmatch(r"\d+년", name) else name


def parse_kosis_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except ValueError:
        # KOSIS는 가끔 키에 따옴표가 없는 JSON을 준다: {ORG_ID:"101"}
        fixed = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', text)
        return json.loads(fixed)


class Kosis(Connector):
    name = "kosis"
    title = "KOSIS 국가통계포털"
    key_envs = ("KOSIS_API_KEY",)
    signup_url = "https://kosis.kr/openapi/ (회원가입 → 활용신청 → 즉시 발급)"
    license = "KOSIS 공공누리"

    def _get(self, path: str, params: dict):
        p = {"apiKey": self.key("KOSIS_API_KEY"), "format": "json", "jsonVD": "Y", **params}
        resp = self.http.get(f"{BASE}/{path}", params=p)
        if resp.status_code != 200:
            raise ApiError("server" if resp.status_code >= 500 else "unknown", f"HTTP {resp.status_code}")
        data = parse_kosis_json(resp.text)
        if isinstance(data, dict) and (data.get("err") or data.get("errCode")):
            code = str(data.get("err") or data.get("errCode"))
            kind, msg = ERR.get(code, ("unknown", data.get("errMsg", "")))
            hint = "https://kosis.kr/openapi/ 에서 키 확인" if kind == "auth" else ""
            raise ApiError(kind, f"KOSIS {code}: {msg}", hint)
        return data

    def _check(self) -> str:
        rows = self._get("statisticsSearch.do", {"method": "getList", "searchNm": "온라인쇼핑", "resultCount": 1})
        return f"통계표 검색 OK ({len(rows)}건)"

    # -------------------------------------------------------- on-demand
    def find_tables(self, query: str, limit: int = 20) -> list[dict]:
        params = {"q": query, "n": limit}
        return self.cached("kosis_search", params, 24 * 30, lambda: self._find(query, limit))

    def _find(self, query: str, limit: int) -> list[dict]:
        try:
            rows = self._get("statisticsSearch.do", {
                "method": "getList", "searchNm": query, "resultCount": limit, "startCount": 1})
        except ApiError as e:
            if e.kind == "no_data":
                return []
            raise
        out = []
        for r in rows:
            out.append({
                "orgId": r.get("ORG_ID"), "tblId": r.get("TBL_ID"), "table": r.get("TBL_NM"),
                "survey": r.get("STAT_NM"), "org": r.get("ORG_NM"), "path": r.get("MT_ATITLE"),
                "range": f"{r.get('STRT_PRD_DE', '')}~{r.get('END_PRD_DE', '')}", "url": r.get("LINK_URL"),
            })
            body = (f"통계표: {r.get('TBL_NM')}\n조사명: {r.get('STAT_NM')}\n작성기관: {r.get('ORG_NM')}\n"
                    f"분류경로: {r.get('MT_ATITLE')}\n수록기간: {r.get('STRT_PRD_DE')}~{r.get('END_PRD_DE')}\n"
                    f"조회키: orgId={r.get('ORG_ID')} tblId={r.get('TBL_ID')}")
            self.store.upsert_document(
                source="kosis", doc_type="stat_table", original_id=f"{r.get('ORG_ID')}/{r.get('TBL_ID')}",
                title=r.get("TBL_NM") or "", body=body, url=r.get("LINK_URL"), license=self.license,
                meta={"orgId": r.get("ORG_ID"), "tblId": r.get("TBL_ID"), "search": query},
            )
        self.store.conn.commit()
        return out

    def table_meta(self, org_id: str, tbl_id: str) -> dict:
        """통계표 구조: 분류 단계(objL1~n)와 수록주기. 조회 조건을 추측하지 않고 정확히 맞추기 위해 쓴다."""
        params = {"orgId": org_id, "tblId": tbl_id}
        return self.cached("kosis_meta", params, 24 * 30, lambda: self._meta(org_id, tbl_id))

    def _meta(self, org_id: str, tbl_id: str) -> dict:
        base = {"method": "getMeta", "orgId": org_id, "tblId": tbl_id}
        itm = self._get("statisticsData.do", {**base, "type": "ITM"})
        prd = self._get("statisticsData.do", {**base, "type": "PRD"})
        levels: dict[int, str] = {}
        for r in itm:
            if r.get("OBJ_ID") != "ITEM" and str(r.get("OBJ_ID_SN") or "").isdigit():
                levels[int(r["OBJ_ID_SN"])] = r.get("OBJ_NM") or ""
        periods = [{"prdSe": prd_code(p.get("PRD_SE")), "name": p.get("PRD_SE"),
                    "start": p.get("STRT_PRD_DE"), "end": p.get("END_PRD_DE")} for p in prd]
        # 가장 최근까지 수록된 주기를 먼저 (예: '년' 2013~2024 > '2년' 2006~2012)
        periods.sort(key=lambda p: (str(p["end"] or "")[:4], str(p["end"] or "")), reverse=True)
        return {"levels": [levels[k] for k in sorted(levels)], "periods": periods,
                "items": sum(r.get("OBJ_ID") == "ITEM" for r in itm)}

    def fetch_table(self, org_id: str, tbl_id: str, prd_se: str = "", recent: int = 24,
                    obj: dict | None = None, itm_id: str = "ALL") -> dict:
        """통계표 최근 n개 시점.

        obj를 생략하면 표의 모든 분류 단계를 ALL로 조회한다. 일부만 주면(예: {"objL1": "13102..."})
        나머지 단계는 ALL로 채운다. prd_se를 생략하면 표에서 가장 최근까지 수록된 주기를 쓴다.
        """
        params = {"orgId": org_id, "tblId": tbl_id, "prdSe": prd_se, "recent": recent,
                  "obj": obj or None, "itmId": itm_id}
        return self.cached("kosis_table", params, 24 * 7, lambda: self._fetch(params))

    def _fetch(self, params: dict) -> dict:
        org, tbl = params["orgId"], params["tblId"]
        try:
            meta = self.table_meta(org, tbl)
        except ApiError as e:
            if e.kind in ("auth", "quota", "network"):
                raise
            meta = None  # 메타 조회가 안 되면 아래에서 수록주기를 차례로 시도
        obj = dict(params.get("obj") or {})
        n_levels = len(meta["levels"]) if meta else 0
        for i in range(1, max(n_levels, 1) + 1):
            obj.setdefault(f"objL{i}", "ALL")
        base = {"method": "getList", "orgId": org, "tblId": tbl, "itmId": params["itmId"], **obj}
        if params["prdSe"]:
            prd_list = [params["prdSe"]]
        elif meta and meta["periods"]:
            prd_list = [meta["periods"][0]["prdSe"]]
        else:
            prd_list = PRD_PROBE
        rows, used = None, None
        for prd in prd_list:
            try:
                rows = self._get("Param/statisticsParameterData.do",
                                 {**base, "prdSe": prd, "newEstPrdCnt": params["recent"]})
                used = prd
                break
            except ApiError as e:
                if e.kind == "no_data" and len(prd_list) > 1:
                    continue  # 수록주기 코드가 틀리면 '결과 없음'이 나오므로 다음 코드 시도
                if e.message.startswith("KOSIS 31:"):
                    raise ApiError(e.kind, f"{org}/{tbl}: {e.message}",
                                   "recent(시점 수)를 줄이거나 obj로 분류를 지정 (예: {\"objL1\": \"<코드>\"}). "
                                   f"분류 단계: {', '.join(meta['levels']) if meta else '알 수 없음'}")
                raise ApiError(e.kind, f"{org}/{tbl}: {e.message}", e.hint)
        if rows is None:
            raise ApiError("no_data", f"{org}/{tbl}: 어떤 수록주기로도 결과 없음",
                           "표 구조(메타)를 확인하지 못해 수록주기를 추측했음. prd_se/obj를 직접 지정해 보세요")
        dataset = f"kosis:{params['orgId']}/{params['tblId']}"
        obs, title = [], ""
        for r in rows:
            title = r.get("TBL_NM") or title
            dims = [r.get(f"C{i}_NM") for i in range(1, 9) if r.get(f"C{i}_NM")]
            key = " | ".join(dims + [r.get("ITM_NM") or ""])
            obs.append({"source": "kosis", "dataset": dataset, "series_key": key, "query_sig": used,
                        "period": r.get("PRD_DE"), "value": to_float(r.get("DT")), "unit": r.get("UNIT_NM"),
                        "dims": {"table": r.get("TBL_NM")}})
        n = self.store.upsert_observations(obs)
        self.store.conn.commit()
        series = sorted({o["series_key"] for o in obs})
        return {"dataset": dataset, "table": title, "prdSe": used, "rows": n,
                "levels": meta["levels"] if meta else None, "obj": obj,
                "series_count": len(series), "series_sample": series[:15],
                "periods": sorted({o["period"] for o in obs})[-6:],
                "how_to_read": "get_series(dataset=...)로 전체 값 조회"}

    # ---------------------------------------------------------- 정기 수집
    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        cad = self.cfg.get("cadence", "monthly")
        return [
            Job(self.name, "catalog", cad, self.sync_catalog, "감시 검색어로 통계표 카탈로그 갱신"),
            Job(self.name, "tables", cad, self.sync_tables, "감시/조회이력 통계표 최신값 갱신"),
        ]

    def sync_catalog(self) -> int:
        n = 0
        for q in self.cfg.get("watch_searches", []):
            n += len(self._find(q, int(self.cfg.get("catalog_limit", 30))))
        return n

    def sync_tables(self) -> int:
        targets = []
        for t in self.cfg.get("watch_tables", []) or []:
            targets.append({"orgId": str(t["orgId"]), "tblId": t["tblId"], "prdSe": t.get("prdSe", ""),
                            "recent": int(t.get("recent", 24)), "obj": t.get("obj") or None,
                            "itmId": t.get("itmId", "ALL")})
        # 에이전트가 검색 중에 조회했던 통계표도 자동으로 감시 대상에 포함 (조회할수록 DB가 자람)
        for (pj,) in self.store.conn.execute("SELECT params_json FROM query_cache WHERE source='kosis_table'"):
            p = json.loads(pj)
            if not any(p["orgId"] == t["orgId"] and p["tblId"] == t["tblId"] for t in targets):
                targets.append(p)
        n = 0
        for t in targets:
            n += self._fetch(t)["rows"]
        return n

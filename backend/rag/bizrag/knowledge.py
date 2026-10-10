"""에이전트가 쓰는 조회 도구 모음. MCP 서버와 CLI가 이 클래스를 공유한다.

원칙
- 먼저 저장된 지식(문서·시계열·원자료)을 조회하고, 없을 때만 on-demand 수집을 부른다.
- on-demand 결과는 DB에 저장되고 캐시되므로, 다음에는 API를 다시 부르지 않는다.
- 모든 결과에 출처·수집시각·주의사항을 함께 돌려준다.
"""
from __future__ import annotations

from typing import Any

from .app import App
from .connectors import ApiError


def _safe(fn):
    def wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except ApiError as e:
            return {"error": e.message, "kind": e.kind, "hint": e.hint}
    wrap.__name__ = fn.__name__
    wrap.__doc__ = fn.__doc__
    return wrap


class Knowledge:
    def __init__(self, app: App | None = None):
        self.app = app or App()
        self.store = self.app.store

    # ------------------------------------------------ 저장된 지식 조회
    def search_knowledge(self, query: str, sources: list[str] | None = None,
                         doc_types: list[str] | None = None, limit: int = 8) -> list[dict]:
        return self.store.search(query, sources=sources, doc_types=doc_types, limit=limit)

    def get_series(self, dataset: str | None = None, series_contains: str | None = None,
                   source: str | None = None, query_sig: str | None = None, limit: int = 500) -> dict:
        rows = self.store.get_series(source=source, dataset=dataset, series_like=series_contains,
                                     query_sig=query_sig, limit=limit)
        grouped: dict[str, dict] = {}
        for r in rows:
            k = f"{r['dataset']} :: {r['series_key']} :: sig={r['query_sig']}"
            g = grouped.setdefault(k, {"unit": r["unit"], "retrieved_at": r["retrieved_at"], "points": []})
            g["points"].append([r["period"], r["value"]])
        return {"series": grouped, "count": len(grouped),
                "note": "같은 query_sig끼리만 직접 비교 가능 (네이버 지수는 상대값)"}

    def find_records(self, source: str | None = None, dataset: str | None = None,
                     contains: str | None = None, limit: int = 50) -> list[dict]:
        return self.store.find_records(source=source, dataset=dataset, contains=contains, limit=limit)

    def inventory(self) -> dict:
        """지금 DB에 무엇이 쌓여 있는지 (에이전트가 처음에 보는 목차)."""
        datasets = [dict(r) for r in self.store.conn.execute(
            """SELECT source, dataset, COUNT(DISTINCT series_key) series, MIN(period) first, MAX(period) last,
                      MAX(retrieved_at) retrieved_at FROM observations GROUP BY source, dataset ORDER BY source""")]
        return {**self.store.stats(), "series_datasets": datasets}

    def source_status(self) -> list[dict]:
        out = []
        for job in self.app.all_jobs():
            due, why = self.app.is_due(job)
            last = self.store.last_success(job.source, job.name)
            out.append({"job": f"{job.source}/{job.name}", "cadence": job.cadence,
                        "last_success": last.isoformat() if last else None, "next": why})
        return out

    # ------------------------------------- on-demand 수집 (결과는 DB에 누적)
    @_safe
    def naver_search_trend(self, keyword_groups: dict[str, list[str]], months: int = 36,
                           time_unit: str = "month", device: str = "", gender: str = "",
                           ages: list[str] | None = None) -> dict:
        return self.app.get("naver").search_trend(keyword_groups, months, time_unit, device, gender, ages)

    @_safe
    def naver_shopping_keywords(self, category_id: str, keywords: list[str], months: int = 36) -> dict:
        return self.app.get("naver").shopping_keyword_trend(category_id, keywords, months)

    @_safe
    def kosis_find_tables(self, query: str, limit: int = 20) -> Any:
        return self.app.get("kosis").find_tables(query, limit)

    @_safe
    def kosis_fetch_table(self, org_id: str, tbl_id: str, prd_se: str = "", recent: int = 24,
                          obj: dict | None = None, itm_id: str = "ALL") -> dict:
        return self.app.get("kosis").fetch_table(org_id, tbl_id, prd_se, recent, obj, itm_id)

    @_safe
    def law_search(self, query: str) -> Any:
        return self.app.get("law").search_laws(query)

    @_safe
    def law_add(self, name: str) -> dict:
        return self.app.get("law").add_law(name)

    @_safe
    def patent_search(self, word: str, rows: int = 30) -> dict:
        return self.app.get("kipris").search_patents(word, rows)

    @_safe
    def worldbank_indicator(self, indicator: str, countries: list[str] | None = None) -> dict:
        return self.app.get("worldbank").indicator(indicator, countries)

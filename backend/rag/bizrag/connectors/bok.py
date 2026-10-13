"""한국은행 경제통계시스템(ECOS) Open API.

- 정기: sources.yaml의 bok.tables에 적은 통계표를 주기마다 최근 n개 시점만 다시 받아 시계열로 저장하고,
  분류별 '최신값·전기 대비·전년 대비' 요약 문서를 만든다 → 에이전트가 "음식점업 영업이익률",
  "60대 소비심리" 같은 말로 검색(RAG)할 수 있다.
- 정기(월): 통계표 카탈로그(검색 가능한 표 목록)를 문서로 저장 → 에이전트가 다른 표도 찾을 수 있다.
- 검색 시: find_tables(검색어), fetch_table(통계코드, 주기) — 결과는 DB에 쌓인다.
- 인증키가 URL 경로에 들어가므로 오류 메시지에 URL을 넣지 않는다.
"""
from __future__ import annotations

import itertools
import json
import re
from collections import defaultdict
from datetime import date, timedelta

from ..util import to_float
from .base import ApiError, Connector, Job

BASE = "https://ecos.bok.or.kr/api"
PAGE = 10000
ERR = {
    "INFO-100": ("auth", "인증키가 유효하지 않음"),
    "INFO-200": ("no_data", "해당하는 데이터가 없음"),
    "ERROR-100": ("input", "필수 값 누락"), "ERROR-101": ("input", "주기와 다른 형식의 날짜"),
    "ERROR-200": ("input", "파일타입 값 오류"), "ERROR-300": ("input", "조회건수 값 누락"),
    "ERROR-301": ("input", "조회건수 값 타입 오류"), "ERROR-400": ("input", "검색범위 초과로 60초 내 응답 실패"),
    "ERROR-500": ("server", "서버 오류"), "ERROR-600": ("server", "DB 연결 오류"),
    "ERROR-601": ("server", "SQL 오류"), "ERROR-602": ("quota", "과도한 호출로 이용 제한"),
}
CYCLE_NAME = {"A": "연간", "S": "반년", "Q": "분기", "M": "월간", "SM": "반월", "D": "일간", "W": "주간"}
YOY_LABEL = {"M": "전년동월", "Q": "전년동기", "W": "52주 전"}
# 새 공표가 있을 때 마지막 저장 시점에서 몇 개 시점 전부터 다시 받을지 (잠정치 수정 반영)
OVERLAP = {"A": 2, "Q": 4, "M": 3, "D": 7}


def period_range(cycle: str, n: int, today: date | None = None) -> tuple[str, str]:
    """최근 n개 시점의 (시작, 끝). 끝은 현재 시점 — ECOS는 아직 없는 시점을 그냥 비워서 돌려준다."""
    t = today or date.today()
    if cycle == "A":
        return str(t.year - n + 1), str(t.year)
    if cycle == "Q":
        q = (t.month - 1) // 3
        s = t.year * 4 + q - n + 1
        return f"{s // 4}Q{s % 4 + 1}", f"{t.year}Q{q + 1}"
    if cycle == "M":
        s = t.year * 12 + t.month - 1 - n + 1
        return f"{s // 12}{s % 12 + 1:02d}", f"{t.year}{t.month:02d}"
    if cycle == "D":
        return (t - timedelta(days=n - 1)).strftime("%Y%m%d"), t.strftime("%Y%m%d")
    raise ApiError("input", f"지원하지 않는 주기: {cycle}")


def shift_period(p: str, cycle: str, k: int) -> str:
    """시점 p를 k개 시점만큼 이동 (k<0이면 과거)."""
    if cycle == "A":
        return str(int(p) + k)
    if cycle == "Q":
        i = int(p[:4]) * 4 + int(p[5]) - 1 + k
        return f"{i // 4}Q{i % 4 + 1}"
    if cycle == "M":
        i = int(p[:4]) * 12 + int(p[4:6]) - 1 + k
        return f"{i // 12}{i % 12 + 1:02d}"
    if cycle == "D":
        return (date(int(p[:4]), int(p[4:6]), int(p[6:8])) + timedelta(days=k)).strftime("%Y%m%d")
    raise ApiError("input", f"지원하지 않는 주기: {cycle}")


def fmt_period(p: str) -> str:
    if re.fullmatch(r"\d{6}", p):
        return f"{p[:4]}.{p[4:]}"
    if re.fullmatch(r"\d{8}", p):
        return f"{p[:4]}.{p[4:6]}.{p[6:]}"
    if re.fullmatch(r"\d{4}Q\d", p):
        return f"{p[:4]}년 {p[5]}분기"
    if re.fullmatch(r"\d{4}", p):
        return f"{p}년"
    return p


def clean_name(name: str | None) -> str:
    """'업황실적BSI 1)' → '업황실적BSI', '전 산 업' → '전산업'."""
    s = re.sub(r"\s*\d+\)\s*$", "", (name or "").strip())
    parts = s.split()
    return "".join(parts) if len(parts) > 1 and all(len(p) == 1 for p in parts) else s


def alias(label: str) -> str:
    """검색용 별칭: '60-70세' → '60-70세 (60대)', '40세미만' → '40세미만 (20대·30대)'."""
    m = re.fullmatch(r"(\d+)-\d+세", label)
    if m:
        return f"{label} ({m.group(1)}대)"
    m = re.fullmatch(r"(\d+)세미만", label)
    if m:
        return f"{label} ({'·'.join(f'{a}대' for a in range(20, int(m.group(1)), 10))})"
    m = re.fullmatch(r"(\d+)세이상", label)
    return f"{label} ({m.group(1)}대 이상)" if m else label


def _num(v: float | None) -> str:
    if v is None:
        return "-"
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.2f}".rstrip("0").rstrip(".")


def weekly_average(points: list[tuple[str, float | None]]) -> list[tuple[str, float, int]]:
    """일간 (YYYYMMDD, 값) → ISO 주별 평균 (YYYY-Www, 평균, 일수)."""
    acc: dict[str, list[float]] = defaultdict(list)
    for p, v in points:
        if v is None:
            continue
        y, w, _ = date(int(p[:4]), int(p[4:6]), int(p[6:])).isocalendar()
        acc[f"{y}-W{w:02d}"].append(v)
    return [(k, round(sum(vs) / len(vs), 2), len(vs)) for k, vs in sorted(acc.items())]


class Bok(Connector):
    name = "bok"
    title = "한국은행 경제통계(ECOS)"
    key_envs = ("BOK_API_KEY",)
    signup_url = "https://ecos.bok.or.kr/api/ (회원가입 → 인증키 신청 → 즉시 발급)"
    license = "한국은행 ECOS (출처 표시)"

    # ------------------------------------------------------------ http
    def _get(self, service: str, *segments) -> dict:
        path = "/".join(str(s) for s in segments)
        resp = self.http.get(f"{BASE}/{service}/{self.key('BOK_API_KEY')}/json/kr/{path}")
        if resp.status_code != 200:
            raise ApiError("server" if resp.status_code >= 500 else "unknown", f"ECOS HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise ApiError("maintenance", "JSON이 아닌 응답: " + resp.text[:120].replace(self.key("BOK_API_KEY"), "***"))
        res = data.get("RESULT")
        if res:
            code = res.get("CODE", "")
            kind, msg = ERR.get(code, ("unknown", res.get("MESSAGE", "")))
            hint = "https://ecos.bok.or.kr/api/ 에서 인증키 확인" if kind == "auth" else ""
            raise ApiError(kind, f"ECOS {code}: {msg}", hint)
        return data.get(service) or {}

    def _rows(self, service: str, *segments) -> list[dict]:
        """페이지를 넘기며 전체 행을 받는다."""
        out, start = [], 1
        while True:
            body = self._get(service, start, start + PAGE - 1, *segments)
            rows = body.get("row") or []
            out += rows
            total = int(body.get("list_total_count") or 0)
            if not rows or len(out) >= total:
                return out
            start += PAGE

    def search(self, stat_code: str, cycle: str, start: str, end: str, items: list[str] | None = None) -> list[dict]:
        """StatisticSearch. items는 분류 1~4 코드 — '?'는 전체. 뒤쪽 '?'는 생략해도 전체로 조회된다."""
        segs = list(items or [])
        while segs and segs[-1] in ("?", "", None):
            segs.pop()
        try:
            return self._rows("StatisticSearch", stat_code, cycle, start, end, *[s or "?" for s in segs])
        except ApiError as e:
            if e.kind == "no_data":
                return []
            raise ApiError(e.kind, f"{stat_code}/{cycle}: {e.message}", e.hint)

    # ----------------------------------------------------------- check
    def _check(self) -> str:
        s, e = period_range("M", 3)
        rows = self.search("523Y001", "M", s, e, ["A001"])
        if not rows:
            return "인증 OK (뉴스심리지수 최근값 없음)"
        r = rows[-1]
        return f"OK (뉴스심리지수 {fmt_period(r['TIME'])}: {r['DATA_VALUE']})"

    # ---------------------------------------------------- 저장 공통
    def _store(self, rows: list[dict], cycle: str) -> tuple[str, str, int]:
        if not rows:
            return "", "", 0
        code, title = rows[0]["STAT_CODE"], rows[0].get("STAT_NAME") or ""
        dataset = f"bok:{code}"
        seq: dict[str, int] = {}
        obs = []
        for r in rows:
            if to_float(r.get("DATA_VALUE")) is None:  # 업종×규모 조합 중 공표되지 않는 칸이 많다
                continue
            codes = [r.get(f"ITEM_CODE{i}") for i in range(1, 5) if r.get(f"ITEM_CODE{i}")]
            names = [clean_name(r.get(f"ITEM_NAME{i}")) for i in range(1, 5) if r.get(f"ITEM_CODE{i}")]
            key = " | ".join(names)
            seq.setdefault(key, len(seq))
            obs.append({"source": "bok", "dataset": dataset, "series_key": key, "query_sig": cycle,
                        "period": r["TIME"], "value": to_float(r.get("DATA_VALUE")), "unit": r.get("UNIT_NAME") or "",
                        "dims": {"codes": codes, "names": names, "seq": seq[key], "table": title}})
        n = self.store.upsert_observations(obs)
        return dataset, title, n

    def _store_weekly(self, dataset: str) -> int:
        """일간 시계열을 주간 평균으로 묶어 query_sig='W'로 저장."""
        n = 0
        series: dict[str, list] = defaultdict(list)
        meta: dict[str, tuple] = {}
        for r in self.store.conn.execute(
                "SELECT series_key, period, value, unit, dims_json FROM observations "
                "WHERE source='bok' AND dataset=? AND query_sig='D' ORDER BY period", (dataset,)):
            series[r[0]].append((r[1], r[2]))
            meta[r[0]] = (r[3], r[4])
        for key, pts in series.items():
            unit, dims = meta[key]
            n += self.store.upsert_observations(
                {"source": "bok", "dataset": dataset, "series_key": key, "query_sig": "W", "period": wk,
                 "value": v, "unit": unit, "dims": {**json.loads(dims or "{}"), "days": days, "agg": "일간 평균"}}
                for wk, v, days in weekly_average(pts))
        return n

    # ------------------------------------------------- 요약 문서 (RAG)
    def _series(self, dataset: str, cycle: str) -> list[dict]:
        rows = self.store.conn.execute(
            "SELECT series_key, period, value, unit, dims_json FROM observations "
            "WHERE source='bok' AND dataset=? AND query_sig=? ORDER BY series_key, period", (dataset, cycle))
        out: dict[str, dict] = {}
        for key, period, value, unit, dims in rows:
            s = out.setdefault(key, {"key": key, "unit": unit, "dims": json.loads(dims or "{}"), "points": []})
            s["points"].append((period, value))
        return sorted(out.values(), key=lambda s: s["dims"].get("seq", 0))

    @staticmethod
    def _stat_line(label: str, s: dict, cycle: str, change: str) -> tuple[str, str] | None:
        pts = [(p, v) for p, v in s["points"] if v is not None]
        if not pts:
            return None
        (lp, lv), unit = pts[-1], s["unit"] or ""
        u = "" if unit in ("", "%") else f" {unit}"

        def delta(old: float | None) -> str:
            if old is None:
                return ""
            if change == "pct":
                return f"{(lv - old) / old * 100:+.1f}%" if old else ""
            return f"{lv - old:+.2f}".rstrip("0").rstrip(".") + ("%p" if unit == "%" else "")

        parts = [f"{_num(lv)}{'%' if unit == '%' else ''}{u}"]
        if len(pts) > 1:
            parts.append(f"{'전년' if cycle == 'A' else '직전'} {_num(pts[-2][1])} ({delta(pts[-2][1])})")
        yoy = None
        if cycle in ("M", "Q"):
            yoy = dict(pts).get(str(int(lp[:4]) - 1) + lp[4:])
        elif cycle == "W" and len(pts) > 52:
            yoy = pts[-53][1]
        if yoy is not None:
            parts.append(f"{YOY_LABEL[cycle]} {_num(yoy)} ({delta(yoy)})")
        window = [v for _, v in pts[-12:]]
        if len(window) >= 4 and cycle != "A":
            parts.append(f"최근 {len(window)}개 시점 평균 {_num(sum(window) / len(window))}, "
                         f"범위 {_num(min(window))}~{_num(max(window))}")
        return lp, f"- {label}: " + " / ".join(parts)

    def _write_docs(self, t: dict, dataset: str, title: str, cycle: str) -> int:
        doc_by = t.get("doc_by")  # 문서를 나눌 분류 위치(1~4). 없으면 표 하나에 문서 하나
        only = {int(k): [str(c) for c in v] for k, v in (t.get("doc_filter") or {}).items()}
        groups: dict[str, list[dict]] = defaultdict(list)
        for s in self._series(dataset, cycle):
            codes, names = s["dims"].get("codes", []), s["dims"].get("names", [])
            if any(len(codes) >= pos and codes[pos - 1] not in cs for pos, cs in only.items()):
                continue
            g = names[doc_by - 1] if doc_by and len(names) >= doc_by else ""
            label = " · ".join(n for i, n in enumerate(names, 1) if i != doc_by) or s["key"]
            groups[g].append({**s, "label": label})
        name = t.get("name") or title
        n = 0
        for g, series in groups.items():
            lines, latest = [], ""
            for s in series:
                r = self._stat_line(s["label"], s, cycle, t.get("change", "diff"))
                if r:
                    latest = max(latest, r[0])
                    lines.append(r[1])
            if not lines:
                continue
            p0 = min(p for s in series for p, _ in s["points"])
            head = [f"한국은행 ECOS {title} ({CYCLE_NAME.get(cycle, cycle)})"]
            if g:
                head.append(f"분류: {alias(g)}")
            head.append(f"기준 시점: {fmt_period(latest)} (DB 수록 {fmt_period(p0)}~{fmt_period(latest)})")
            if t.get("note"):
                head.append(f"해석: {t['note']}")
            if t.get("keywords"):
                head.append(f"관련어: {', '.join(t['keywords'])}")
            tail = f"\n전체 값: get_series(dataset=\"{dataset}\"" + (f", series_contains=\"{g}\"" if g else "") + ")"
            n += self.store.upsert_document(  # 내용이 같으면 재색인하지 않음
                source="bok", doc_type=t.get("doc_type", "econ_indicator"),
                original_id=f"{t['stat_code']}:{cycle}:{g or 'all'}",
                title=f"[한국은행] {name}" + (f" — {g}" if g else "") + f" ({fmt_period(latest)} 기준)",
                body="\n".join(head) + "\n\n" + "\n".join(lines) + tail,
                url="https://ecos.bok.or.kr/", published_at=latest, license=self.license,
                meta={"stat_code": t["stat_code"], "cycle": cycle, "group": g, "dataset": dataset},
            )
        return n

    # ---------------------------------------------------------- 정기 수집
    @property
    def tables(self) -> list[dict]:
        return [t for t in (self.cfg.get("tables") or []) if t.get("enabled", True) and t.get("stat_code")]

    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        jobs = [Job(self.name, "catalog", self.cfg.get("catalog_cadence", "monthly"), self.sync_catalog,
                    "ECOS 통계표 목록 → 카탈로그 문서")]
        for t in self.tables:
            jobs.append(Job(self.name, f"table:{t.get('id') or t['stat_code']}", t.get("cadence", "monthly"),
                            (lambda t=t: self.sync_table(t)), t.get("name", t["stat_code"])))
        return jobs

    # ------------------------------------------------ 갱신 확인 (증분 수집)
    def latest_available(self, stat_code: str, cycle: str) -> str | None:
        """ECOS에 공표된 최신 시점. 항목 목록(가벼운 호출 1번)의 END_TIME 최댓값. 확인 못 하면 None."""
        try:
            rows = self._rows("StatisticItemList", stat_code)
        except ApiError as e:
            if e.kind in ("auth", "quota", "network"):
                raise
            return None
        ends = [str(r["END_TIME"]) for r in rows if r.get("CYCLE") == cycle and r.get("END_TIME")]
        return max(ends) if ends else None

    def stored_range(self, stat_code: str, cycle: str) -> tuple[str | None, str | None]:
        r = self.store.conn.execute(
            "SELECT MIN(period), MAX(period) FROM observations WHERE source='bok' AND dataset=? AND query_sig=?",
            (f"bok:{stat_code}", cycle)).fetchone()
        return r[0], r[1]

    def plan(self, stat_code: str, cycle: str, history: int) -> tuple[str | None, str, str]:
        """(받을 시작 시점 또는 None=받을 것 없음, 끝 시점, 설명)."""
        start, end = period_range(cycle, history)
        p0, p1 = self.stored_range(stat_code, cycle)
        if p1 is None or p0 > start:  # 처음이거나, history를 늘려 과거가 비어 있으면 전체
            return start, end, "최초/전체 수집"
        latest = self.latest_available(stat_code, cycle)
        if latest is not None and latest <= p1:
            return None, end, f"새 공표 없음 (최신 {fmt_period(latest)}, 기존 RAG 유지)"
        since = max(start, shift_period(p1, cycle, -OVERLAP.get(cycle, 3)))
        what = f"새 공표 {fmt_period(latest)}" if latest else "공표 시점 확인 실패"
        return since, end, f"{what} → {fmt_period(since)}부터 증분 수집"

    def sync_table(self, t: dict) -> tuple[int, str]:
        cycle = t.get("cycle", "M")
        start, end, note = self.plan(t["stat_code"], cycle, int(t.get("history", 36)))
        if start is None:
            return 0, note
        # items: 분류 위치별 코드. 문자열 하나 또는 목록(목록이면 조합마다 호출). 생략 시 전체
        slots = [v if isinstance(v, list) else [v] for v in (t.get("items") or [])]
        rows: list[dict] = []
        for combo in itertools.product(*slots) if slots else [()]:
            rows += self.search(t["stat_code"], cycle, start, end, [str(c) for c in combo])
        if not rows:
            if self.stored_range(t["stat_code"], cycle)[1]:
                return 0, note + " — 받은 행 없음, 기존 RAG 유지"
            raise ApiError("no_data", f"{t['stat_code']}/{cycle} {start}~{end}: 데이터 없음",
                           "sources.yaml의 stat_code·cycle·items 확인")
        dataset, title, n = self._store(rows, cycle)
        doc_cycle = cycle
        if t.get("weekly") and cycle == "D":
            n += self._store_weekly(dataset)
            doc_cycle = "W"
        docs = self._write_docs(t, dataset, title, doc_cycle)
        self.store.conn.commit()
        return n, f"{note}, 요약 문서 {docs}개 갱신"

    def _table_list(self) -> list[dict]:
        return self.cached("bok_tables", {}, 24 * 7, lambda: self._rows("StatisticTableList"))

    def sync_catalog(self) -> tuple[int, str]:
        rows = self._rows("StatisticTableList")
        by_code = {r["STAT_CODE"]: r for r in rows}

        def path(r):
            names, p, seen = [], r.get("P_STAT_CODE"), set()
            while p in by_code and p not in seen:
                seen.add(p)
                names.append(by_code[p]["STAT_NAME"])
                p = by_code[p].get("P_STAT_CODE")
            return " > ".join(reversed(names))

        n = total = 0
        for r in rows:
            if r.get("SRCH_YN") != "Y":
                continue
            total += 1
            cyc = r.get("CYCLE") or ""
            body = (f"통계표: {r['STAT_NAME']}\n분류경로: {path(r)}\n주기: {CYCLE_NAME.get(cyc, cyc)}\n"
                    f"작성기관: {r.get('ORG_NAME') or '한국은행'}\n"
                    f"조회키: bok_fetch_table(stat_code=\"{r['STAT_CODE']}\", cycle=\"{cyc}\")")
            n += self.store.upsert_document(source="bok", doc_type="stat_table", original_id=r["STAT_CODE"],
                                            title=r["STAT_NAME"], body=body, url="https://ecos.bok.or.kr/",
                                            license=self.license, meta={"stat_code": r["STAT_CODE"], "cycle": cyc})
        self.store.conn.commit()
        return n, f"통계표 {total}개 중 새로 생기거나 바뀐 것 {n}개"

    # -------------------------------------------------------- on-demand
    def find_tables(self, query: str, limit: int = 20) -> list[dict]:
        words = query.split()
        hits = [r for r in self._table_list()
                if r.get("SRCH_YN") == "Y" and all(w in (r.get("STAT_NAME") or "") for w in words)]
        return [{"stat_code": r["STAT_CODE"], "table": r["STAT_NAME"], "cycle": r.get("CYCLE")} for r in hits[:limit]]

    def items(self, stat_code: str) -> list[dict]:
        """통계표의 분류·항목 코드 (fetch_table의 items를 정할 때 쓴다)."""
        rows = self.cached("bok_items", {"c": stat_code}, 24 * 30,
                           lambda: self._rows("StatisticItemList", stat_code))
        return [{"group": r.get("GRP_NAME"), "code": r.get("ITEM_CODE"), "name": clean_name(r.get("ITEM_NAME")),
                 "cycle": r.get("CYCLE"), "range": f"{r.get('START_TIME')}~{r.get('END_TIME')}",
                 "unit": r.get("UNIT_NAME")} for r in rows]

    def fetch_table(self, stat_code: str, cycle: str, items: list[str] | None = None, recent: int = 24) -> dict:
        params = {"c": stat_code, "cy": cycle, "items": items or [], "n": recent}
        return self.cached("bok_table", params, 24 * 7, lambda: self._fetch(stat_code, cycle, items, recent))

    def _from_db(self, stat_code: str, cycle: str, items: list[str] | None, start: str) -> dict | None:
        """요청 범위가 DB에 이미 있고 그 뒤 새 공표가 없으면 API 대신 DB로 답한다."""
        p0, p1 = self.stored_range(stat_code, cycle)
        if p1 is None or p0 > start:
            return None
        want = [str(c) for c in (items or [])]
        keys, title = [], ""
        for key, dims in self.store.conn.execute(
                "SELECT DISTINCT series_key, dims_json FROM observations WHERE source='bok' AND dataset=? "
                "AND query_sig=?", (f"bok:{stat_code}", cycle)):
            d = json.loads(dims or "{}")
            codes = d.get("codes", [])
            if all(w in ("?", "") or (i < len(codes) and codes[i] == w) for i, w in enumerate(want)):
                keys.append((d.get("seq", 0), key))
                title = d.get("table", title)
        if not keys:
            return None
        latest = self.latest_available(stat_code, cycle)
        if latest is None or latest > p1:
            return None
        keys = [k for _, k in sorted(keys)]
        periods = [r[0] for r in self.store.conn.execute(
            "SELECT DISTINCT period FROM observations WHERE source='bok' AND dataset=? AND query_sig=? "
            "AND period>=? ORDER BY period", (f"bok:{stat_code}", cycle, start))]
        dataset = f"bok:{stat_code}"
        return {"dataset": dataset, "table": title, "cycle": cycle, "rows": 0, "series_count": len(keys),
                "series_sample": keys[:15], "periods": periods[-6:],
                "from": f"DB (새 공표 없음, 최신 {fmt_period(latest)}) — API 재수집 생략",
                "how_to_read": f"get_series(dataset=\"{dataset}\")로 전체 값 조회"}

    def _fetch(self, stat_code: str, cycle: str, items: list[str] | None, recent: int) -> dict:
        start, end = period_range(cycle, recent)
        cached = self._from_db(stat_code, cycle, items, start)
        if cached:
            return cached
        rows = self.search(stat_code, cycle, start, end, items)
        if not rows:
            raise ApiError("no_data", f"{stat_code}/{cycle} {start}~{end}: 데이터 없음",
                           "bok_table_items로 주기·분류 코드 확인")
        dataset, title, n = self._store(rows, cycle)
        self.store.conn.commit()
        keys = list(dict.fromkeys(" | ".join(clean_name(r.get(f"ITEM_NAME{i}")) for i in range(1, 5)
                                             if r.get(f"ITEM_CODE{i}")) for r in rows))
        return {"dataset": dataset, "table": title, "cycle": cycle, "rows": n, "series_count": len(keys),
                "series_sample": keys[:15], "periods": sorted({r["TIME"] for r in rows})[-6:],
                "how_to_read": f"get_series(dataset=\"{dataset}\")로 전체 값 조회"}

"""국가법령정보 공동활용 (법제처 DRF).

- 월 1회: 감시 법령 목록의 현행 버전(MST)을 확인해 바뀌었으면 조문 전체를 다시 적재
- 검색 시: search_laws(검색어) 목록 조회, add_law(법령명) 으로 지식베이스에 추가
  (add_law로 추가한 법령은 이후 월 1회 개정 확인 대상에 자동 포함)
- 조문 하나가 RAG 문서 하나. AI 해석이 아니라 원문을 그대로 저장한다.
"""
from __future__ import annotations

import json
import re

from .base import ApiError, Connector, Job

BASE = "https://www.law.go.kr/DRF"


def _norm(s: str) -> str:
    return re.sub(r"[\s·ㆍ・]", "", s or "")


def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _text_of(node) -> list[str]:
    """조문 JSON 안의 '…내용' 필드를 순서대로 모은다 (항·호·목 중첩 대응)."""
    out: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and k.endswith("내용"):
                out.append(v.strip())
            elif isinstance(v, (dict, list)):
                out.extend(_text_of(v))
    elif isinstance(node, list):
        for v in node:
            if isinstance(v, str):
                out.append(v.strip())
            else:
                out.extend(_text_of(v))
    return [t for t in out if t]


class Law(Connector):
    name = "law"
    title = "국가법령정보 (법제처)"
    key_envs = ("LAW_OC",)
    signup_url = "https://open.law.go.kr (회원가입 → OPEN API 신청, OC=가입 이메일 @앞부분, 호출할 PC의 공인IP 또는 도메인 등록)"
    license = "공공저작물(법령) — 출처 표시"

    def _get(self, path: str, params: dict) -> dict:
        p = {"OC": self.key("LAW_OC"), "type": "JSON", **params}
        resp = self.http.get(f"{BASE}/{path}", params=p,
                             headers={"Referer": "https://www.law.go.kr/"})
        text = resp.text.strip()
        if "사용자 정보 검증" in text or "미신청" in text:
            raise ApiError("not_approved", "법제처가 사용자 검증을 거부",
                           "open.law.go.kr > 마이페이지에서 OPEN API 신청 승인 여부와 등록한 IP/도메인이 지금 PC와 같은지 확인")
        if resp.status_code != 200:
            raise ApiError("server" if resp.status_code >= 500 else "unknown", f"HTTP {resp.status_code}")
        if not text or text.startswith("<"):
            raise ApiError("maintenance", "빈 응답 또는 HTML(점검 페이지) 응답", "잠시 후 재시도")
        return json.loads(text)

    def _check(self) -> str:
        data = self._get("lawSearch.do", {"target": "law", "query": "소비자기본법", "display": 1})
        total = (data.get("LawSearch") or {}).get("totalCnt")
        return f"법령 검색 OK (totalCnt={total})"

    # -------------------------------------------------------- on-demand
    def search_laws(self, query: str, display: int = 20) -> list[dict]:
        params = {"query": query, "display": display}
        return self.cached("law_search", params, 24 * 30, lambda: self._search(query, display))

    def _search(self, query: str, display: int = 20) -> list[dict]:
        data = self._get("lawSearch.do", {"target": "law", "query": query, "display": display})
        out = []
        for r in _as_list((data.get("LawSearch") or {}).get("law")):
            out.append({
                "name": r.get("법령명한글"), "mst": r.get("법령일련번호"), "law_id": r.get("법령ID"),
                "kind": r.get("법령구분명"), "ministry": r.get("소관부처명"),
                "enforced": r.get("시행일자"), "promulgated": r.get("공포일자"),
                "url": ("https://www.law.go.kr" + r["법령상세링크"]) if r.get("법령상세링크") else None,
            })
        return out

    def add_law(self, name: str) -> dict:
        """법령명을 지식베이스에 추가(조문 전체 적재)하고 월간 개정 확인 대상으로 등록."""
        res = self._ingest_by_name(name)
        self.store.cache_put("law_watch", {"name": name}, {"name": name}, 24 * 365 * 10)
        return res

    def _ingest_by_name(self, name: str) -> dict:
        # 가운뎃점(·/ㆍ) 표기 차이로 검색이 빗나가는 경우를 대비해 몇 가지 검색어로 시도
        queries = [name, name.replace("·", "ㆍ"), max(re.split(r"[\s·ㆍ]", name), key=len)]
        hits, exact = [], []
        for q in dict.fromkeys(queries):
            hits = self._search(q, 50)
            exact = [h for h in hits if _norm(h["name"]) == _norm(name)]
            if exact:
                break
        exact = exact or hits[:1]
        if not exact:
            raise ApiError("no_data", f"'{name}' 법령을 찾지 못함")
        h = exact[0]
        if self.store.has_version("law", h["name"], str(h["mst"])):
            return {"name": h["name"], "mst": h["mst"], "status": "변경 없음"}
        n = self._ingest_mst(str(h["mst"]), h)
        self.store.mark_version("law", h["name"], str(h["mst"]), f"시행 {h['enforced']}", n)
        self.store.conn.commit()
        return {"name": h["name"], "mst": h["mst"], "enforced": h["enforced"], "articles": n, "status": "적재"}

    def _ingest_mst(self, mst: str, meta: dict) -> int:
        data = self._get("lawService.do", {"target": "law", "MST": mst})
        law = data.get("법령") or data
        basic = law.get("기본정보") or {}
        law_name = basic.get("법령명_한글") or meta.get("name")
        enforced = basic.get("시행일자") or meta.get("enforced")
        units = _as_list((law.get("조문") or {}).get("조문단위"))
        n = 0
        for u in units:
            if u.get("조문여부") and u.get("조문여부") != "조문":
                continue  # 장·절 제목 행 제외
            no = str(u.get("조문번호", "")) + (f"의{u['조문가지번호']}" if u.get("조문가지번호") else "")
            title = f"{law_name} 제{no}조" + (f"({u['조문제목']})" if u.get("조문제목") else "")
            body = "\n".join(_text_of(u))
            if not body:
                continue
            self.store.upsert_document(
                source="law", doc_type="law_article", original_id=f"{law_name}:{no}",
                title=title, body=body, url=meta.get("url"), published_at=enforced,
                license=self.license,
                meta={"law": law_name, "mst": mst, "article": no, "enforced": enforced,
                      "ministry": meta.get("ministry"), "verification": "원문"},
            )
            n += 1
        return n

    # ---------------------------------------------------------- 정기 수집
    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        return [Job(self.name, "watched_laws", self.cfg.get("cadence", "monthly"),
                    self.sync_watched, "감시 법령 개정 확인 및 조문 재적재")]

    def sync_watched(self) -> int:
        names = list(self.cfg.get("watch_laws", []) or [])
        for (pj,) in self.store.conn.execute("SELECT params_json FROM query_cache WHERE source='law_watch'"):
            nm = json.loads(pj)["name"]
            if nm not in names:
                names.append(nm)
        n, errors = 0, []
        for nm in names:
            try:
                r = self._ingest_by_name(nm)
                n += r.get("articles", 0)
            except ApiError as e:
                if e.kind in ("auth", "not_approved", "missing_key"):
                    raise
                errors.append(f"{nm}: {e.message}")
        if errors:
            print("  [법령] 일부 실패:", "; ".join(errors))
        return n

"""국가법령정보 공동활용 — 법원 판례(判例) 수집기.

- 정기(월): watch_topics 키워드별로 최근 판례를 검색해 새 판례만 적재
- 검색 시: search_precedents(query) 로 on-demand 검색 + 30일 캐시
- 판례 하나가 RAG 문서 하나 (doc_type='court_precedent')
  title: 법원명 + 사건번호 + 사건명
  body: 판시사항 + 판결요지 + 참조조문
"""
from __future__ import annotations

import json

from .base import ApiError, Connector, Job
from .law import _as_list

BASE = "https://www.law.go.kr/DRF"


def _strip(v) -> str:
    """None 및 빈 값을 빈 문자열로 정규화."""
    return (v or "").strip()


class LawPrecedent(Connector):
    name = "law_precedent"
    title = "국가법령정보 판례 (법제처)"
    key_envs = ("LAW_OC",)
    signup_url = (
        "https://open.law.go.kr (회원가입 → OPEN API 신청, "
        "OC=가입 이메일 @앞부분, 호출할 PC의 공인IP 또는 도메인 등록)"
    )
    license = "공공저작물(판례) — 출처 표시"

    # ─────────────────────────────────────────── 내부 HTTP
    def _get(self, path: str, params: dict) -> dict:
        p = {"OC": self.key("LAW_OC"), "type": "JSON", **params}
        resp = self.http.get(
            f"{BASE}/{path}", params=p,
            headers={"Referer": "https://www.law.go.kr/"},
        )
        text = resp.text.strip()
        if "사용자 정보 검증" in text or "미신청" in text:
            raise ApiError(
                "not_approved",
                "법제처가 사용자 검증을 거부",
                "open.law.go.kr > 마이페이지에서 OPEN API 신청 승인 여부와 "
                "등록한 IP/도메인이 지금 PC와 같은지 확인",
            )
        if resp.status_code != 200:
            raise ApiError(
                "server" if resp.status_code >= 500 else "unknown",
                f"HTTP {resp.status_code}",
            )
        if not text or text.startswith("<"):
            raise ApiError("maintenance", "빈 응답 또는 HTML(점검 페이지) 응답", "잠시 후 재시도")
        return json.loads(text)

    # ─────────────────────────────────────────── check
    def _check(self) -> str:
        data = self._get("lawSearch.do", {"target": "prec", "query": "소비자", "display": 1})
        total = (data.get("PrecSearch") or {}).get("totalCnt", "?")
        return f"판례 검색 OK (totalCnt={total})"

    # ─────────────────────────────────────────── on-demand 검색
    def search_precedents(self, query: str, display: int = 20) -> list[dict]:
        """키워드로 판례 목록 반환 (30일 캐시)."""
        return self.cached(
            "prec_search", {"q": query, "n": display}, 24 * 30,
            lambda: self._search(query, display),
        )

    def _search(self, query: str, display: int = 20) -> list[dict]:
        data = self._get("lawSearch.do", {"target": "prec", "query": query, "display": display})
        out = []
        for r in _as_list((data.get("PrecSearch") or {}).get("prec")):
            out.append({
                "seq": _strip(r.get("판례일련번호")),
                "case_name": _strip(r.get("사건명")),
                "case_no": _strip(r.get("사건번호")),
                "decided": _strip(r.get("선고일자")),
                "court": _strip(r.get("법원명")),
                "verdict_type": _strip(r.get("판결유형")),
                "summary": _strip(r.get("판시사항")),
                "url": (
                    "https://www.law.go.kr" + r["판례상세링크"]
                    if r.get("판례상세링크") else None
                ),
            })
        return out

    # ─────────────────────────────────────────── 판례 상세 적재
    def _ingest_seq(self, seq: str, meta: dict) -> bool:
        """판례 일련번호로 상세 조회해 DB에 upsert. 새 문서면 True."""
        data = self._get("lawService.do", {"target": "prec", "MST": seq})
        prec = data.get("판례") or data

        # 기본정보
        basic = prec.get("기본정보") or {}
        court = _strip(basic.get("법원명") or meta.get("court"))
        case_no = _strip(basic.get("사건번호") or meta.get("case_no"))
        case_name = _strip(basic.get("사건명") or meta.get("case_name"))
        decided = _strip(basic.get("선고일자") or meta.get("decided"))
        verdict_type = _strip(basic.get("판결유형") or meta.get("verdict_type"))

        # 판시사항 / 판결요지 / 참조조문 / 참조판례
        sections: list[str] = []
        for key, label in [
            ("판시사항", "【판시사항】"),
            ("판결요지", "【판결요지】"),
            ("참조조문", "【참조조문】"),
            ("참조판례", "【참조판례】"),
        ]:
            val = _strip(prec.get(key))
            if val:
                sections.append(f"{label}\n{val}")

        body = "\n\n".join(sections)
        if not body:
            return False

        title = f"[{court}] {case_no} — {case_name}" if case_no else f"[{court}] {case_name}"
        url = meta.get("url") or f"https://www.law.go.kr/lsInfoP.do?precSeq={seq}"

        return self.store.upsert_document(
            source="law_precedent",
            doc_type="court_precedent",
            original_id=seq,
            title=title,
            body=body,
            url=url,
            published_at=decided.replace(".", "").replace("-", "")[:8] if decided else None,
            license=self.license,
            meta={
                "seq": seq,
                "case_no": case_no,
                "case_name": case_name,
                "court": court,
                "decided": decided,
                "verdict_type": verdict_type,
                "verification": "원문",
            },
        )

    # ─────────────────────────────────────────── 정기 수집
    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        return [
            Job(
                self.name, "watched_topics",
                self.cfg.get("cadence", "monthly"),
                self.sync_watched,
                "판례 주제별 신규 판례 수집",
            )
        ]

    def sync_watched(self) -> int:
        topics: list[str] = list(self.cfg.get("watch_topics") or [])
        display = int(self.cfg.get("display_per_topic", 30))
        total = 0
        for topic in topics:
            try:
                hits = self._search(topic, display)
            except ApiError as e:
                if e.kind in ("auth", "not_approved", "missing_key"):
                    raise
                print(f"  [판례] '{topic}' 검색 실패: {e.message}")
                continue
            for hit in hits:
                seq = hit.get("seq")
                if not seq:
                    continue
                # 이미 적재된 seq는 건너뜀 (upsert 내부에서도 처리되지만 API 절약)
                try:
                    added = self._ingest_seq(seq, hit)
                    if added:
                        total += 1
                except ApiError as e:
                    if e.kind in ("auth", "not_approved", "missing_key"):
                        raise
                    print(f"  [판례] seq={seq} 상세 실패: {e.message}")
            self.store.conn.commit()
        return total

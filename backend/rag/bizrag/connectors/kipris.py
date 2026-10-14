"""KIPRIS Plus 특허·실용신안 키워드 검색 (검색 시 호출 + 결과 적재).

특허 검색 결과는 '유사 기술 후보'일 뿐, 침해·독점 여부 판단 근거가 아니다.
"""
from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET

from .base import ApiError, Connector

BASE = "https://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"


def _t(el, tag):
    if el is None:
        return None
    for c in el:
        if c.tag.lower() == tag.lower():
            return (c.text or "").strip() or None
    return None


class Kipris(Connector):
    name = "kipris"
    title = "KIPRIS Plus 특허"
    key_envs = ("KIPRIS_API_KEY",)
    signup_url = "https://plus.kipris.or.kr (회원가입 → 데이터 상품 '특허·실용 공개·등록공보' 무료 이용 신청 → 마이페이지에서 키 확인)"
    license = "KIPRIS Plus 이용약관"

    def _search_raw(self, word: str, rows: int = 20, page: int = 1, year: int = 0) -> ET.Element:
        params = {"word": word, "year": year, "patent": "true", "utility": "true",
                  "numOfRows": rows, "pageNo": page,
                  "ServiceKey": urllib.parse.unquote(self.key("KIPRIS_API_KEY"))}
        resp = self.http.get(f"{BASE}/getWordSearch", params=params,
                             headers={"Accept": "application/xml"})
        if resp.status_code != 200:
            raise ApiError("server" if resp.status_code >= 500 else "unknown", f"HTTP {resp.status_code}")
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            raise ApiError("maintenance", "XML이 아닌 응답: " + resp.text[:120])
        header = root.find(".//header")
        code = _t(header, "resultCode") or _t(header, "successYN")
        msg = _t(header, "resultMsg") or ""
        if code not in (None, "00", "0", "Y") and (code or msg):
            kind = "auth" if any(s in msg for s in ("키", "Key", "KEY", "인증")) else "unknown"
            raise ApiError(kind, f"KIPRIS {code}: {msg}",
                           "plus.kipris.or.kr 마이페이지에서 해당 상품 이용신청 승인과 키를 확인" if kind == "auth" else "")
        return root

    def _check(self) -> str:
        root = self._search_raw("배터리", rows=1)
        total = root.findtext(".//totalCount")
        return f"특허 검색 OK (totalCount={total})"

    def search_patents(self, word: str, rows: int = 30, year: int = 0) -> dict:
        params = {"word": word, "rows": rows, "year": year}
        return self.cached("kipris_search", params, 24 * 30, lambda: self._search(word, rows, year))

    def _search(self, word: str, rows: int, year: int) -> dict:
        root = self._search_raw(word, rows=rows, year=year)
        items = []
        for it in root.iter("item"):
            d = {
                "application_number": _t(it, "applicationNumber"), "title": _t(it, "inventionTitle"),
                "applicant": _t(it, "applicantName"), "ipc": _t(it, "ipcNumber"),
                "application_date": _t(it, "applicationDate"), "open_date": _t(it, "openDate"),
                "register_status": _t(it, "registerStatus"), "abstract": _t(it, "astrtCont"),
            }
            items.append(d)
            if d["application_number"]:
                self.store.upsert_document(
                    source="kipris", doc_type="patent", original_id=d["application_number"],
                    title=d["title"] or "", body=f"{d['title']}\n출원인: {d['applicant']}\nIPC: {d['ipc']}\n"
                                                  f"상태: {d['register_status']}\n\n{d['abstract'] or ''}",
                    url="https://www.kipris.or.kr",
                    published_at=d["application_date"], license=self.license,
                    meta={**{k: v for k, v in d.items() if k != "abstract"}, "search": word},
                )
        self.store.conn.commit()
        by_applicant: dict[str, int] = {}
        by_year: dict[str, int] = {}
        for d in items:
            by_applicant[d["applicant"] or "?"] = by_applicant.get(d["applicant"] or "?", 0) + 1
            y = (d["application_date"] or "")[:4]
            by_year[y] = by_year.get(y, 0) + 1
        return {"word": word, "total": root.findtext(".//totalCount"), "returned": len(items),
                "top_applicants": sorted(by_applicant.items(), key=lambda x: -x[1])[:8],
                "by_year": dict(sorted(by_year.items())),
                "items": [{k: v for k, v in d.items() if k != "abstract"} for d in items[:15]],
                "note": "유사 기술 후보 목록. 침해·독점 가능성은 전문가 검토 필요"}

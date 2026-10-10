"""공공데이터포털(data.go.kr).

1) 파일데이터 자동변환 API (api.odcloud.kr)
   - 데이터셋 ID만 설정하면, 공개 명세(infuser.odcloud.kr)에서 버전 목록(uddi 경로)을 자동으로 찾아
     '아직 안 받은 새 버전'만 적재한다. 매번 전체를 다시 받지 않는다.
   - 데이터셋마다 포털에서 '활용신청'을 해야 키가 통한다 (키 1개 + 데이터셋별 신청).
   - aggregate 설정이 있으면 행을 집계해 시계열(observations)과 요약 문서(RAG)도 만든다.
     예) 소비자 피해구제: 물품명×청구이유 건수 → "어떤 품목에서 어떤 불만이 늘었나"

2) 일반 REST API (apis.data.go.kr) — 엔드포인트·필드를 설정 파일에 적어 쓰는 범용 수집기
"""
from __future__ import annotations

import urllib.parse
from collections import Counter, defaultdict

from ..util import find_date8
from ..store import stable_hash
from .base import ApiError, Connector, Job, status_to_kind

ODCLOUD = "https://api.odcloud.kr/api"
OAS = "https://infuser.odcloud.kr/oas/docs"


class DataGoKr(Connector):
    name = "datagokr"
    title = "공공데이터포털"
    key_envs = ("DATA_GO_KR_SERVICE_KEY",)
    signup_url = "https://www.data.go.kr (회원가입 → 마이페이지 > 일반 인증키(Decoding) 복사, 데이터셋별 '활용신청' 필요)"
    license = "공공누리 (데이터셋별 확인)"

    def _key(self) -> str:
        return urllib.parse.unquote(self.key("DATA_GO_KR_SERVICE_KEY"))

    @property
    def datasets(self) -> list[dict]:
        return [d for d in (self.cfg.get("file_datasets") or []) if d.get("enabled", True) and d.get("id")]

    # ------------------------------------------------------------ 명세 탐색
    def versions(self, dataset_id: str) -> dict:
        """데이터셋의 자동변환 API 버전 목록 (최신순). 키 불필요."""
        resp = self.http.get(OAS, params={"namespace": f"{dataset_id}/v1"})
        if resp.status_code != 200:
            raise ApiError("input", f"명세 조회 실패 HTTP {resp.status_code}")
        spec = resp.json()
        title = (spec.get("info") or {}).get("title", "")
        out = []
        for path, ops in (spec.get("paths") or {}).items():
            summary = ((ops.get("get") or {}).get("summary")) or ""
            out.append({"path": path, "label": summary, "date": find_date8(summary) or ""})
        out.sort(key=lambda v: v["date"], reverse=True)
        if not out:
            raise ApiError("config", f"{dataset_id} ({title or '제목 없음'}): 자동변환 API가 없음",
                           "포털에서 CSV를 받아 inbox/ 폴더에 넣으면 적재됨")
        return {"title": title, "versions": out}

    def _page(self, path: str, page: int, per_page: int) -> dict:
        resp = self.http.get(f"{ODCLOUD}{path}", params={
            "page": page, "perPage": per_page, "returnType": "JSON", "serviceKey": self._key()})
        if resp.status_code == 200:
            return resp.json()
        try:
            body = resp.json()
            msg = f"{body.get('code', '')} {body.get('msg', '')}".strip()
        except ValueError:
            msg = resp.text[:150]
        kind = status_to_kind(resp.status_code)
        hint = ""
        if resp.status_code in (401, 403):
            kind = "not_approved" if "등록" in msg or resp.status_code == 403 else "auth"
            hint = "data.go.kr에서 이 데이터셋 '활용신청' 했는지 확인 (승인 후 반영까지 1~2시간 걸릴 수 있음). 키는 Decoding 키 사용"
        raise ApiError(kind, f"HTTP {resp.status_code} {msg}", hint)

    # --------------------------------------------------------------- check
    def _check(self) -> str:
        if not self.datasets:
            return "키 입력됨 (설정된 데이터셋 없음)"
        ok, bad = [], []
        for d in self.datasets:
            try:
                v = self.versions(str(d["id"]))["versions"][0]
                self._page(v["path"], 1, 1)
                ok.append(d.get("name", d["id"]))
            except ApiError as e:
                bad.append(f"{d.get('name', d['id'])}: {e}")
        if bad and not ok:
            raise ApiError("not_approved", "모든 데이터셋 실패 — " + " / ".join(bad),
                           "각 데이터셋 페이지에서 '활용신청' 필요")
        msg = f"OK {len(ok)}개 ({', '.join(ok)})"
        if bad:
            msg += " | 실패: " + " / ".join(bad)
        return msg

    # ------------------------------------------------------------ 정기 수집
    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        jobs = []
        for d in self.datasets:
            jobs.append(Job(self.name, f"file:{d['id']}", d.get("cadence", "monthly"),
                            (lambda d=d: self.sync_dataset(d)), d.get("name", "")))
        return jobs

    def sync_dataset(self, d: dict) -> int:
        ds_id = str(d["id"])
        info = self.versions(ds_id)
        # 처음 실행 시 최근 backfill개 버전, 이후에는 새로 올라온 버전만
        new = [v for v in info["versions"][: int(d.get("backfill", 1))]
               if not self.store.has_version("datagokr", ds_id, v["path"])]
        total = 0
        for v in reversed(new):
            rows = self._all_rows(v["path"], int(d.get("max_rows", 200000)))
            n = self.store.insert_records("datagokr", ds_id, v["date"] or v["path"], rows)
            if d.get("aggregate"):
                self._aggregate(d, info["title"], v, rows)
            if d.get("as_documents"):
                self._rows_to_docs(d, v, rows)
            self.store.mark_version("datagokr", ds_id, v["path"], v["label"], len(rows))
            self.store.conn.commit()
            total += n
        return total

    def _all_rows(self, path: str, max_rows: int) -> list[dict]:
        rows, page, per = [], 1, 1000
        while True:
            data = self._page(path, page, per)
            batch = data.get("data") or []
            rows.extend(batch)
            if not batch or len(rows) >= min(int(data.get("totalCount") or 0), max_rows):
                break
            page += 1
        return rows[:max_rows]

    def _aggregate(self, d: dict, title: str, v: dict, rows: list[dict]) -> None:
        cfg = d["aggregate"]
        keys = cfg["group_by"]  # 예: ["물품명", "청구이유"]
        missing = [k for k in keys if rows and k not in rows[0]]
        if missing:
            raise ApiError("config", f"{d['id']} aggregate.group_by 필드 없음: {missing}",
                           f"sources.yaml 수정. 실제 필드: {list(rows[0])}")
        period = v["date"][:6] or v["label"]
        cnt = Counter(tuple(str(r.get(k, "")).strip() for k in keys) for r in rows)
        self.store.upsert_observations({
            "source": "datagokr", "dataset": f"agg:{d['id']}", "series_key": " | ".join(k),
            "query_sig": "+".join(keys), "period": period, "value": c, "unit": "건수",
            "dims": dict(zip(keys, k)),
        } for k, c in cnt.items())
        # 첫 번째 그룹 키(예: 품목)별 요약 문서 → 에이전트가 "OO 품목 소비자 불만"으로 검색 가능
        by_first: dict[str, Counter] = defaultdict(Counter)
        for k, c in cnt.items():
            by_first[k[0]][" / ".join(k[1:]) or "전체"] += c
        top_n = int(cfg.get("min_count", 3))
        for item, sub in by_first.items():
            total = sum(sub.values())
            if not item or total < top_n:
                continue
            lines = [f"{name}: {c}건 ({c / total:.0%})" for name, c in sub.most_common(10)]
            self.store.upsert_document(
                source="datagokr", doc_type=cfg.get("doc_type", "dataset_summary"),
                original_id=f"{d['id']}:{period}:{item}",
                title=f"{d.get('name', title)} — {item} ({v['label']})",
                body=f"{keys[0]} '{item}' 관련 {total}건, {' / '.join(keys[1:])} 분포:\n" + "\n".join(lines),
                url=f"https://www.data.go.kr/data/{d['id']}/fileData.do", published_at=v["date"],
                license=self.license, meta={"dataset": d["id"], "version": v["label"], "item": item, "total": total},
            )

    def _rows_to_docs(self, d: dict, v: dict, rows: list[dict]) -> None:
        cfg = d["as_documents"]
        tf, bf = cfg.get("title_fields", []), cfg.get("body_fields")
        for i, r in enumerate(rows):
            title = " ".join(str(r.get(f, "")) for f in tf).strip() or f"{d.get('name')} #{i}"
            fields = bf or list(r.keys())
            body = "\n".join(f"{f}: {r.get(f)}" for f in fields if r.get(f) not in (None, ""))
            oid = str(r.get(cfg.get("id_field", ""), "")) or str(i)
            self.store.upsert_document(
                source="datagokr", doc_type=cfg.get("doc_type", "dataset_row"),
                original_id=f"{d['id']}:{oid}", title=title, body=body,
                url=f"https://www.data.go.kr/data/{d['id']}/fileData.do", published_at=v["date"],
                license=self.license, meta={"dataset": d["id"], "version": v["label"]},
            )


class DataGoKrRest(Connector):
    """apis.data.go.kr 계열 REST API를 설정만으로 수집 (예: KOTRA 해외시장뉴스).

    sources.yaml의 datagokr_rest.apis 항목:
      endpoint, params, items_path(점 경로), id_field, title_field, body_fields, date_field, cadence
    """

    name = "datagokr_rest"
    title = "공공데이터포털 REST API"
    key_envs = ("DATA_GO_KR_SERVICE_KEY",)
    signup_url = DataGoKr.signup_url
    license = "공공누리 (API별 확인)"

    @property
    def apis(self) -> list[dict]:
        return [a for a in (self.cfg.get("apis") or []) if a.get("enabled") and a.get("endpoint")]

    def _call(self, a: dict, extra: dict | None = None) -> list[dict]:
        params = {"serviceKey": urllib.parse.unquote(self.key("DATA_GO_KR_SERVICE_KEY")),
                  "type": "json", "_type": "json", **(a.get("params") or {}), **(extra or {})}
        resp = self.http.get(a["endpoint"], params=params)
        text = resp.text.strip()
        if resp.status_code != 200 or text.startswith("<"):
            if "SERVICE_KEY_IS_NOT_REGISTERED" in text or "SERVICE KEY" in text.upper():
                raise ApiError("not_approved", "등록되지 않은 서비스키", "이 API '활용신청' 필요")
            raise ApiError(status_to_kind(resp.status_code) if resp.status_code != 200 else "input",
                           f"HTTP {resp.status_code} {text[:150]}")
        node = resp.json()
        for part in a.get("items_path", "response.body.items.item").split("."):
            node = (node or {}).get(part) if isinstance(node, dict) else None
        if node is None:
            return []
        return node if isinstance(node, list) else [node]

    def _check(self) -> str:
        if not self.apis:
            return "활성화된 REST API 없음 (sources.yaml에서 endpoint 설정 후 enabled: true)"
        res = []
        for a in self.apis:
            items = self._call(a, {"numOfRows": 1, "pageNo": 1})
            res.append(f"{a['name']} OK({len(items)})")
        return ", ".join(res)

    def jobs(self) -> list[Job]:
        if self.missing_keys():
            return []
        return [Job(self.name, f"rest:{a['name']}", a.get("cadence", "daily"), (lambda a=a: self.sync_api(a)),
                    a.get("description", "")) for a in self.apis]

    def sync_api(self, a: dict) -> int:
        n = 0
        for page in range(1, int(a.get("pages", 3)) + 1):
            items = self._call(a, {"numOfRows": a.get("rows", 100), "pageNo": page})
            if not items:
                break
            for it in items:
                body = "\n".join(str(it.get(f, "")) for f in a.get("body_fields", []) if it.get(f))
                if not body:
                    continue
                if self.store.upsert_document(
                    source="datagokr_rest", doc_type=a.get("doc_type", a["name"]),
                    original_id=str(it.get(a.get("id_field", ""), "") or stable_hash(body)),
                    title=str(it.get(a.get("title_field", ""), "")), body=body,
                    url=it.get(a.get("url_field", "")) if a.get("url_field") else None,
                    published_at=it.get(a.get("date_field", "")) if a.get("date_field") else None,
                    license=self.license, meta={"api": a["name"]},
                ):
                    n += 1
            self.store.conn.commit()
        return n

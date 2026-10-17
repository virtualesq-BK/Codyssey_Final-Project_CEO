"""소량 샘플 수집 테스트.

- 실제 DB(data/knowledge.db)는 건드리지 않고 data/sample_test.db 에만 저장합니다.
- 소스마다 1~2회 호출만 합니다 (호출 한도 부담 없음).
- KIPRIS는 키 발급 대기 중이라 건너뜁니다. LAW_OC가 비어 있으면 법령도 건너뜁니다.
- 결과는 화면과 logs/sample_test_<시각>.txt 에 함께 기록됩니다.

실행:  .venv\\Scripts\\python.exe sample_test.py
"""
from __future__ import annotations

import io
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bizrag.app import App  # noqa: E402
from bizrag.connectors import ApiError  # noqa: E402
from bizrag.store import Store  # noqa: E402

(ROOT / "logs").mkdir(exist_ok=True)
(ROOT / "data").mkdir(exist_ok=True)
LOG = ROOT / "logs" / f"sample_test_{datetime.now():%Y%m%d_%H%M%S}.txt"
_buf = io.StringIO()


def out(s=""):
    print(s)
    _buf.write(s + "\n")


def j(o, n=500):
    return json.dumps(o, ensure_ascii=False, default=str)[:n]


results: list[tuple[str, str, str]] = []  # (이름, 상태, 메모)


def step(name, fn, skip_reason=""):
    out(f"\n▶ {name}")
    if skip_reason:
        out(f"   ⬜ 건너뜀: {skip_reason}")
        results.append((name, "SKIP", skip_reason))
        return None
    try:
        r = fn()
        out(f"   ✅ {j(r)}")
        results.append((name, "OK", ""))
        return r
    except ApiError as e:
        out(f"   ❌ {e}")
        results.append((name, "FAIL", str(e)))
    except Exception as e:  # noqa: BLE001
        out(f"   ❌ {type(e).__name__}: {e}")
        out("   " + traceback.format_exc().replace("\n", "\n   ")[-800:])
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))
    return None


db_path = ROOT / "data" / "sample_test.db"
app = App(root=ROOT, store=Store(db_path))
env = app.env
has = lambda k: bool((env.get(k) or "").strip())  # noqa: E731

out(f"bizrag 소량 샘플 테스트 — {datetime.now():%Y-%m-%d %H:%M:%S}")
out(f"테스트 DB: {db_path}")
out("키 입력 상태: " + ", ".join(f"{k}={'O' if has(k) else 'X'}" for k in
    ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KOSIS_API_KEY", "LAW_OC", "DATA_GO_KR_SERVICE_KEY", "KIPRIS_API_KEY"]))

# 1) 키·권한 점검 (KIPRIS 제외)
out("\n[1] 키·권한 점검")
for r in app.check([n for n in app.connectors if n != "kipris"]):
    mark = "✅" if r.ok else ("⬜" if r.kind == "missing_key" else "❌")
    out(f"   {mark} {r.title:<22} {r.message}")
    if r.hint and not r.ok:
        out(f"      └ {r.hint}")

out("\n[2] 소량 수집")
naver_ok = has("NAVER_CLIENT_ID") and has("NAVER_CLIENT_SECRET")
c = app.connectors

step("네이버 검색어 트렌드 (텀블러, 12개월)",
     lambda: (lambda r: {k: r.get(k) for k in ("query_sig", "period", "summary")})(
         c["naver"].search_trend({"텀블러": ["텀블러"]}, 12, "month", "", "", None)),
     "" if naver_ok else "네이버 키 미입력")

step("네이버 쇼핑 키워드 클릭 추이 (생활/건강: 텀블러·보온병, 12개월)",
     lambda: (lambda r: {k: r.get(k) for k in ("query_sig", "summary")})(
         c["naver"].shopping_keyword_trend("50000008", ["텀블러", "보온병"], 12)),
     "" if naver_ok else "네이버 키 미입력")

step("KOSIS 통계표 탐색 (온라인쇼핑 거래액, 3건)",
     lambda: [{k: t[k] for k in ("orgId", "tblId", "table")} for t in c["kosis"].find_tables("온라인쇼핑 거래액", 3)],
     "" if has("KOSIS_API_KEY") else "KOSIS 키 미입력")
# 검색 순위 1위가 원하는 표가 아닐 수 있어, 값 조회는 온라인쇼핑동향 표(101/DT_1KE10041)로 고정
step("KOSIS 표 값 조회 (온라인쇼핑몰 상품군별 거래액, 최근 3개 시점)",
     lambda: {k: v for k, v in c["kosis"].fetch_table("101", "DT_1KE10041", "", 3).items()
              if k in ("table", "prdSe", "rows", "levels", "series_count", "periods")},
     "" if has("KOSIS_API_KEY") else "KOSIS 키 미입력")

step("법령 검색 (화장품법)",
     lambda: [f"{l['name']} (시행 {l['enforced']})" for l in c["law"].search_laws("화장품법", 3)],
     "" if has("LAW_OC") else "LAW_OC 미입력 (.env)")

step("World Bank 인구 (KOR·JPN, 최근 3년)",
     lambda: c["worldbank"].indicator("SP.POP.TOTL", ["KOR", "JPN"], 3))

# 공공데이터포털: 데이터셋별 최신 버전에서 3행만 받아 보기 (저장은 records 테이블에 샘플로)
if "datagokr" in c:
    ds = c["datagokr"]
    for d in ds.datasets:
        def _probe(d=d):
            info = ds.versions(d["id"])
            v = info["versions"][0]
            page = ds._page(v["path"], 1, 3)
            rows = page.get("data") or []
            return {"title": info["title"], "latest_version": v["label"], "totalCount": page.get("totalCount"),
                    "fields": list(rows[0].keys())[:12] if rows else [], "rows_received": len(rows)}
        step(f"공공데이터포털 {d['id']} {d.get('name', '')} (3행)", _probe,
             "" if has("DATA_GO_KR_SERVICE_KEY") else "DATA_GO_KR_SERVICE_KEY 미입력")

step("KIPRIS 특허", lambda: None, "키 발급 대기 중 (3일 후 테스트)")

# 3) 저장 확인 + 캐시 확인 (두 번째 호출은 API를 다시 부르지 않아야 함)
out("\n[3] 캐시 동작 확인")
if naver_ok and any(n.startswith("네이버 쇼핑") and s == "OK" for n, s, _ in results):
    r2 = c["naver"].shopping_keyword_trend("50000008", ["텀블러", "보온병"], 12)
    out(f"   네이버 쇼핑 키워드 재호출 → _cache={r2.get('_cache', 'miss')} (hit이면 정상)")
else:
    out("   건너뜀: 네이버 쇼핑 키워드 조회가 실패해 캐시를 확인할 수 없음")

out("\n[4] 테스트 DB에 쌓인 양")
out("   " + j(app.store.stats(), 2000))

out("\n[요약]")
for n, s, m in results:
    out(f"   {dict(OK='✅', FAIL='❌', SKIP='⬜')[s]} {n}" + (f" — {m[:150]}" if m else ""))
ok = sum(s == "OK" for _, s, _ in results)
fail = sum(s == "FAIL" for _, s, _ in results)
out(f"\n성공 {ok} / 실패 {fail} / 건너뜀 {len(results) - ok - fail}")
out(f"로그: {LOG}")
LOG.write_text(_buf.getvalue(), encoding="utf-8")

"""bizrag 명령행.

  python -m bizrag check                키·권한 점검 (소스별 ✅/❌ + 원인)
  python -m bizrag sync                 주기가 된 소스만 수집 (하루 1번 예약 실행)
  python -m bizrag sync --force         주기 무시하고 전부 수집
  python -m bizrag status               소스별 마지막 수집·다음 예정 + DB 현황
  python -m bizrag search "검색어"      저장된 문서 검색 (--mode auto|keyword|semantic|hybrid)
  python -m bizrag try "키워드"         검색 시 수집(on-demand) 시험: 네이버·특허·법령·KOSIS
  python -m bizrag discover 15083256    공공데이터포털 파일데이터의 버전/자동API 확인
  python -m bizrag precedent-search "키워드"  법원 판례 on-demand 검색 (결과 DB 저장)
  python -m bizrag pinecone-init        Pinecone Serverless 인덱스 점검 및 자동 생성
  python -m bizrag pinecone-sync        SQLite 문서 청크들을 Pinecone으로 일괄 임베딩 & 전송
  python -m bizrag pinecone-search "질의" Pinecone 벡터 유사도 검색 테스트
  python -m bizrag mcp                  에이전트용 MCP 서버 실행
"""
from __future__ import annotations

import argparse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _p(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def cmd_check(app, args):
    print("\n[API 키·권한 점검]\n")
    results = app.check(args.only)
    ok = 0
    for r in results:
        mark = "✅" if r.ok else ("⬜" if r.kind == "missing_key" else "❌")
        ok += r.ok
        print(f"{mark} {r.title:<22} {r.message}")
        if r.hint and not r.ok:
            print(f"   └ {r.hint}")
    print(f"\n{ok}/{len(results)} 소스 사용 가능. (⬜ = 키 미입력, ❌ = 키는 있으나 실패)\n")


def cmd_sync(app, args):
    print(f"\n[수집 {'(강제)' if args.force else ''}]\n")
    res = app.sync(force=args.force, only=args.only)
    ok = sum(r["status"] == "ok" for r in res)
    err = sum(r["status"] == "error" for r in res)
    print(f"\n완료: 성공 {ok} / 실패 {err} / 건너뜀 {len(res) - ok - err}\n")


def cmd_status(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    print("\n[수집 일정]")
    for s in k.source_status():
        print(f"  {s['job']:<34} {s['cadence']:<9} 마지막 성공: {s['last_success'] or '-':<26} {s['next']}")
    print("\n[최근 실행 결과]")
    for r in app.store.run_summary():
        print(f"  {r['source']}/{r['job']:<28} {r['last_status']:<7} {(r['last_message'] or '')[:90]}")
    print("\n[DB 현황]")
    _p(k.inventory())


def cmd_search(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    mode = getattr(args, "mode", "auto")
    results = k.search_knowledge(args.query, limit=args.limit, mode=mode)
    if not results:
        print(f"\n'{args.query}'에 대한 검색 결과가 없습니다 (mode={mode}).\n")
        return
    print(f"\n[문서 검색 결과: '{args.query}' (mode={mode})]")
    for i, h in enumerate(results, 1):
        score_info = f"score {h.get('score', '-')}"
        if "hybrid_score" in h:
            score_info = f"hybrid_score {h['hybrid_score']} (rank fusion)"
        print(f"\n#{i} [{h.get('source')}/{h.get('doc_type')}] {h.get('title')}  ({score_info})")
        text = (h.get('text') or '')[:300].replace('\n', ' ')
        print(f"   {text}")
        print(f"   출처: {h.get('url') or '-'} | 수집 {h.get('retrieved_at')}")
    print()


def cmd_pinecone_init(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    if not k.pinecone:
        print("\n❌ PINECONE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.\n")
        return
    print(f"\n[Pinecone 인덱스 점검/생성: '{k.pinecone.index_name}']")
    print(f"  - Cloud/Region: {k.pinecone.cloud}/{k.pinecone.region}")
    print(f"  - Embedding Provider: {k.pinecone.embeddings.provider} ({k.pinecone.embeddings.model}, {k.pinecone.embeddings.dimension}차원)")
    created = k.pinecone.ensure_index()
    if created:
        print(f"  ✅ 새 인덱스 '{k.pinecone.index_name}' 생성 요청 완료 (준비 중)")
    else:
        print(f"  ✅ 기존 인덱스 '{k.pinecone.index_name}' 확인 완료")
    try:
        stats = k.pinecone.stats()
        print(f"  - 현재 저장된 벡터 수: {stats.get('total_vector_count', 0)}")
        print(f"  - 네임스페이스 현황: {stats.get('namespaces', {})}")
    except Exception as e:
        print(f"  ⚠️ 인덱스 초기화 직후이거나 통계 조회 중: {e}")
    print()


def cmd_pinecone_sync(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    if not k.pinecone:
        print("\n❌ PINECONE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.\n")
        return
    print("\n[Pinecone 동기화 시작]")
    chunks = app.store.get_all_chunks(limit=args.limit)
    if not chunks:
        print("  동기화할 청크가 SQLite DB에 없습니다. 먼저 'python -m bizrag sync' 등을 실행하세요.\n")
        return
    print(f"  - 대상 청크: 총 {len(chunks)}개")
    print(f"  - Pinecone 인덱스: {k.pinecone.index_name} (namespace={k.pinecone.namespace})")
    print(f"  - 임베딩 모델: {k.pinecone.embeddings.provider} / {k.pinecone.embeddings.model}")

    batch_size = args.batch_size
    upserted = k.pinecone.upsert_chunks(chunks, batch_size=batch_size)
    print(f"  ✅ {upserted}개 청크 Pinecone 업서트 완료!\n")


def cmd_pinecone_search(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    if not k.pinecone:
        print("\n❌ PINECONE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.\n")
        return
    print(f"\n[Pinecone 시맨틱 검색: '{args.query}']")
    hits = k.pinecone.search(args.query, limit=args.limit)
    if not hits:
        print("  검색 결과가 없습니다.")
    for i, h in enumerate(hits, 1):
        print(f"\n#{i} [{h.get('source')}/{h.get('doc_type')}] {h.get('title')}  (유사도: {h.get('score')})")
        text = (h.get('text') or '')[:300].replace('\n', ' ')
        print(f"   {text}")
        print(f"   출처: {h.get('url') or '-'} | 수집 {h.get('retrieved_at')}")
    print()


def cmd_try(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    kw = args.keyword
    print(f"\n[검색 시 수집 시험: '{kw}'] — 결과는 DB에 저장되고 다음 호출은 캐시를 씁니다\n")
    tests = [
        ("네이버 검색어 트렌드", lambda: k.naver_search_trend({kw: [kw]}, months=24)["summary"]),
        ("KOSIS 통계표 탐색", lambda: [t["table"] for t in k.kosis_find_tables(kw, 5)]),
        ("법령 검색", lambda: [f"{l['name']} (시행 {l['enforced']})" for l in k.law_search(kw)[:5]]),
        ("KIPRIS 특허", lambda: {key: v for key, v in k.patent_search(kw, 20).items()
                                if key in ("total", "top_applicants", "by_year")}),
    ]
    for name, fn in tests:
        try:
            out = fn()
            if isinstance(out, dict) and "error" in out:
                print(f"❌ {name}: [{out['kind']}] {out['error']} {('→ ' + out['hint']) if out.get('hint') else ''}")
            else:
                print(f"✅ {name}:")
                print("   " + json.dumps(out, ensure_ascii=False, default=str)[:600])
        except (KeyError, TypeError) as e:
            print(f"❌ {name}: 응답 형식 확인 필요 ({e})")
    print()


def cmd_discover(app, args):
    ds = app.get("datagokr") if "datagokr" in app.connectors else None
    if ds is None:
        from .connectors import DataGoKr
        ds = DataGoKr({}, app.env, app.store)
    info = ds.versions(args.dataset_id)
    print(f"\n{args.dataset_id}: {info['title']} — 자동변환 API 버전 {len(info['versions'])}개 (최신 5개)")
    for v in info["versions"][:5]:
        print(f"  {v['date'] or '-':<9} {v['label']}\n            {v['path']}")
    if not ds.missing_keys():
        try:
            row = ds._page(info["versions"][0]["path"], 1, 1).get("data", [{}])
            print("\n필드:", ", ".join((row[0] if row else {}).keys()))
        except Exception as e:  # noqa: BLE001
            print(f"\n샘플 조회 실패: {e}")
    print("\nsources.yaml > datagokr > file_datasets 에 id를 추가하면 정기 수집됩니다.\n")


def cmd_precedent_search(app, args):
    from .knowledge import Knowledge
    k = Knowledge(app)
    query = args.query
    display = args.display
    print(f"\n[법원 판례 검색: '{query}' (최대 {display}건)]\n")
    results = k.precedent_search(query, display)
    if isinstance(results, dict) and "error" in results:
        print(f"❌ [{results['kind']}] {results['error']}")
        if results.get("hint"):
            print(f"   → {results['hint']}")
        return
    if not results:
        print("  검색 결과가 없습니다.")
        return
    for i, r in enumerate(results, 1):
        print(f"#{i} [{r.get('court')}] {r.get('case_no')} — {r.get('case_name')}  ({r.get('decided')})")
        summary = (r.get("summary") or "").replace("\n", " ")[:200]
        if summary:
            print(f"   {summary}")
        if r.get("url"):
            print(f"   {r['url']}")
    print(f"\n총 {len(results)}건 (결과는 DB에 캐시됩니다)\n")


def cmd_mcp(app, args):
    from .knowledge import Knowledge
    from .mcp_server import build
    build(Knowledge(app)).run()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bizrag", description="사업 아이디어 평가용 RAG 데이터 수집기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check"); s.add_argument("--only", nargs="*")
    s = sub.add_parser("sync"); s.add_argument("--force", action="store_true"); s.add_argument("--only", nargs="*")
    sub.add_parser("status")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=8)
    s.add_argument("--mode", choices=["auto", "keyword", "semantic", "hybrid"], default="auto")
    s = sub.add_parser("try"); s.add_argument("keyword")
    s = sub.add_parser("discover"); s.add_argument("dataset_id")
    s = sub.add_parser("precedent-search")
    s.add_argument("query")
    s.add_argument("--display", type=int, default=20, help="검색 결과 최대 건수")
    sub.add_parser("mcp")

    # Pinecone Vector RAG 전용 커맨드
    sub.add_parser("pinecone-init")
    s = sub.add_parser("pinecone-sync")
    s.add_argument("--limit", type=int, default=None, help="동기화할 최대 청크 수")
    s.add_argument("--batch-size", type=int, default=100, help="한 번에 업서트할 청크 수")
    s = sub.add_parser("pinecone-search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=8)

    args = ap.parse_args(argv)

    from .app import App
    from .connectors import ApiError
    app = App()
    dispatch = {
        "check": cmd_check,
        "sync": cmd_sync,
        "status": cmd_status,
        "search": cmd_search,
        "try": cmd_try,
        "discover": cmd_discover,
        "mcp": cmd_mcp,
        "precedent-search": cmd_precedent_search,
        "pinecone-init": cmd_pinecone_init,
        "pinecone-sync": cmd_pinecone_sync,
        "pinecone-search": cmd_pinecone_search,
    }
    try:
        dispatch[args.cmd](app, args)
    except ApiError as e:
        print(f"오류: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()

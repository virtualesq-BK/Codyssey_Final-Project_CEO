"""모의 응답으로 전체 흐름을 검증한다 (네트워크 불필요).

실행: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class FakeResp:
    def __init__(self, status=200, body=None, text=None):
        self.status_code = status
        if text is None:
            text = json.dumps(body, ensure_ascii=False)
        self.text = text
        self.content = text.encode("utf-8")

    def json(self):
        return json.loads(self.text)


PATENT_XML = """<?xml version="1.0" encoding="UTF-8"?><response><header><resultCode>00</resultCode>
<resultMsg>NORMAL SERVICE.</resultMsg></header><body><items>
<item><applicationNumber>1020240001234</applicationNumber><inventionTitle>시약 재고 관리 시스템</inventionTitle>
<applicantName>주식회사 랩툴</applicantName><ipcNumber>G06Q 10/08</ipcNumber><applicationDate>20240105</applicationDate>
<registerStatus>공개</registerStatus><astrtCont>연구실 시약의 유효기간과 재고를 클라우드로 관리한다.</astrtCont></item>
</items><numOfRows>1</numOfRows><pageNo>1</pageNo><totalCount>1</totalCount></body></response>"""

LAW_DETAIL = {"법령": {"기본정보": {"법령명_한글": "소비자기본법", "시행일자": "20240101"},
                      "조문": {"조문단위": [
                          {"조문번호": "1", "조문여부": "전문", "조문내용": "제1장 총칙"},
                          {"조문번호": "1", "조문여부": "조문", "조문제목": "목적",
                           "조문내용": "제1조(목적) 이 법은 소비자의 권익을 증진하기 위하여…"},
                          {"조문번호": "17", "조문여부": "조문", "조문제목": "청약철회",
                           "조문내용": "제17조(청약철회)", "항": [{"항내용": "① 소비자는 7일 이내에 청약철회를 할 수 있다."}]},
                      ]}}}

SWAGGER_3040720 = {"info": {"title": "한국소비자원 소비자 피해구제 정보"}, "paths": {
    "/3040720/v1/uddi:old": {"get": {"summary": "한국소비자원_소비자 피해구제 정보_20260331"}},
    "/3040720/v1/uddi:new": {"get": {"summary": "한국소비자원_소비자 피해구제 정보_20260630"}},
}}
# 실제 데이터처럼 ID 칸이 없어 같은 내용의 행이 여러 번 나온다
RELIEF_ROWS = ([{"물품명": "헬스장", "청구이유": "계약해제"} for _ in range(5)] +
               [{"물품명": "헬스장", "청구이유": "부당행위"} for _ in range(2)] +
               [{"물품명": "무선이어폰", "청구이유": "품질"} for _ in range(4)])


class Router:
    """URL 패턴 → 가짜 응답."""

    def __init__(self):
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        p = kw.get("params") or {}
        if "naverapihub" in url:
            h = kw.get("headers") or {}
            if not (h.get("X-NCP-APIGW-API-KEY-ID") and h.get("X-NCP-APIGW-API-KEY")):
                return FakeResp(401, body={"error": {"errorCode": "200", "message": "Authentication Failed"}})
        if "/search-trend/v1/search" in url:
            groups = kw["json"]["keywordGroups"]
            return FakeResp(body={"results": [
                {"title": g["groupName"], "keywords": g["keywords"],
                 "data": [{"period": f"2025-{m:02d}-01", "ratio": 50 + m} for m in range(1, 13)] +
                         [{"period": f"2026-{m:02d}-01", "ratio": 60 + m} for m in range(1, 10)]}
                for g in groups]})
        if "/shopping/v1/categories" in url:
            return FakeResp(body={"results": [
                {"title": c["name"], "category": c["param"], "data": [{"period": "2026-08-01", "ratio": 70}]}
                for c in kw["json"]["category"]]})
        if "/shopping/v1/category/age" in url or "/shopping/v1/category/gender" in url:
            return FakeResp(body={"results": [{"title": "x", "data": [
                {"period": "2026-08-01", "group": "20", "ratio": 40}, {"period": "2026-08-01", "group": "30", "ratio": 60}]}]})
        if "/shopping/v1/category/keywords" in url:
            return FakeResp(body={"results": [
                {"title": k["name"], "keyword": k["param"], "data": [{"period": "2026-08-01", "ratio": 80}]}
                for k in kw["json"]["keyword"]]})
        if "statisticsSearch.do" in url:
            if p.get("searchNm") == "없는통계":
                return FakeResp(body={"err": "30", "errMsg": "데이터가 존재하지 않습니다."})
            return FakeResp(text='[{ORG_ID:"101",ORG_NM:"통계청",TBL_ID:"DT_1KE10041",TBL_NM:"온라인쇼핑 거래액",'
                                 'STAT_NM:"온라인쇼핑동향조사",MT_ATITLE:"도소매 > 온라인쇼핑",STRT_PRD_DE:"2017",END_PRD_DE:"2026",'
                                 'LINK_URL:"https://kosis.kr/x"}]')
        if "statisticsData.do" in url and p.get("tblId") == "DT_JP51":  # 분류 2단계 표의 메타
            if p.get("type") == "ITM":
                return FakeResp(body=[
                    {"OBJ_ID": "ITEM", "OBJ_NM": "항목", "ITM_ID": "T1", "ITM_NM": "보급률"},
                    {"OBJ_ID": "A", "OBJ_NM": "상거래현대화수준별", "OBJ_ID_SN": "1", "ITM_ID": "a1"},
                    {"OBJ_ID": "B", "OBJ_NM": "지역별", "OBJ_ID_SN": "2", "ITM_ID": "b1"}])
            return FakeResp(body=[{"PRD_SE": "2년", "STRT_PRD_DE": "2006", "END_PRD_DE": "2012"},
                                  {"PRD_SE": "년", "STRT_PRD_DE": "2013", "END_PRD_DE": "2024"}])
        if "statisticsParameterData.do" in url and p.get("tblId") == "DT_JP51":
            if not p.get("objL2"):
                return FakeResp(body={"err": "20", "errMsg": "필수요청변수값이 누락되었습니다. (objL)"})
            if p.get("prdSe") != "Y":
                return FakeResp(body={"err": "30", "errMsg": "데이터가 존재하지 않습니다."})
            return FakeResp(body=[{"TBL_NM": "상거래현대화수준", "PRD_DE": "2024", "C1_NM": "POS 기기",
                                   "C2_NM": "서울", "ITM_NM": "보급률", "UNIT_NM": "%", "DT": "42.1"}])
        if "statisticsParameterData.do" in url:
            if p.get("prdSe") != "M":  # 수록주기 자동 탐색 검증
                return FakeResp(body={"err": "30", "errMsg": "데이터가 존재하지 않습니다."})
            return FakeResp(body=[{"TBL_NM": "온라인쇼핑 거래액", "PRD_DE": f"2026{m:02d}", "C1_NM": "식품",
                                   "ITM_NM": "거래액", "UNIT_NM": "백만원", "DT": str(1000 + m)} for m in range(1, 7)])
        if "lawSearch.do" in url:
            if p.get("OC") == "bad":
                return FakeResp(text="사용자 정보 검증에 실패하였습니다.")
            return FakeResp(body={"LawSearch": {"totalCnt": "1", "law": {
                "법령명한글": "소비자기본법", "법령일련번호": "253527", "법령ID": "001", "시행일자": "20240101",
                "소관부처명": "공정거래위원회", "법령상세링크": "/DRF/lawService.do?MST=253527"}}})
        if "lawService.do" in url:
            return FakeResp(body=LAW_DETAIL)
        if "getWordSearch" in url:
            return FakeResp(text=PATENT_XML)
        if "worldbank.org" in url:
            return FakeResp(body=[{"page": 1}, [
                {"indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
                 "country": {"id": "KR", "value": "Korea, Rep."}, "countryiso3code": "KOR",
                 "date": "2025", "value": 51700000}]])
        if "infuser.odcloud.kr" in url:
            return FakeResp(body=SWAGGER_3040720 if "3040720" in p.get("namespace", "") else {"info": {}, "paths": {}})
        if "api.odcloud.kr" in url:
            if p.get("serviceKey") == "unapproved":
                return FakeResp(401, body={"code": -4, "msg": "등록되지 않은 인증키 입니다."})
            rows = RELIEF_ROWS
            per, page = int(p["perPage"]), int(p["page"])
            return FakeResp(body={"totalCount": len(rows), "data": rows[(page - 1) * per: page * per]})
        return FakeResp(404, body={"error": url})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "config").mkdir()
        shutil.copy(ROOT / "config" / "sources.yaml", self.tmp / "config" / "sources.yaml")
        self.env_backup = dict(os.environ)
        os.environ.update({
            "NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "sec", "KOSIS_API_KEY": "k",
            "LAW_OC": "me", "KIPRIS_API_KEY": "k%2B1", "DATA_GO_KR_SERVICE_KEY": "dk",
        })
        from bizrag.app import App
        from bizrag.connectors import Http
        self.router = Router()
        http = Http(); http.request = self.router.request  # 네트워크 대신 라우터
        self.app = App(self.tmp, http=http)

    def tearDown(self):
        self.app.store.close()
        os.environ.clear(); os.environ.update(self.env_backup)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestTextIndex(unittest.TestCase):
    def test_korean_two_char_words(self):
        from bizrag.store import Store
        s = Store(Path(tempfile.mkdtemp()) / "t.db")
        s.upsert_document(source="t", doc_type="d", original_id="1", title="연구실 시약관리 서비스",
                          body="대학 연구실의 시약 재고를 관리하는 클라우드 서비스")
        s.upsert_document(source="t", doc_type="d", original_id="2", title="헬스장", body="헬스장 계약해제 분쟁")
        s.conn.commit()
        self.assertEqual(s.search("시약")[0]["doc_id"], "t:d:1")
        self.assertEqual(s.search("시약을 관리")[0]["doc_id"], "t:d:1")   # 조사·띄어쓰기 달라도
        self.assertEqual(s.search("계약 해제")[0]["doc_id"], "t:d:2")
        self.assertFalse(s.upsert_document(source="t", doc_type="d", original_id="2",
                                           title="헬스장", body="헬스장 계약해제 분쟁"))  # 동일 내용은 재색인 안 함


class TestCheck(Base):
    def test_check_all_ok(self):
        res = {r.source: r for r in self.app.check()}
        for name in ("naver", "kosis", "law", "kipris", "worldbank", "datagokr"):
            self.assertTrue(res[name].ok, f"{name}: {res[name].message}")

    def test_missing_and_bad_keys(self):
        os.environ["LAW_OC"] = "bad"
        os.environ["DATA_GO_KR_SERVICE_KEY"] = "unapproved"
        del os.environ["KOSIS_API_KEY"]
        from bizrag.app import App
        app = App(self.tmp, store=self.app.store, http=self.app.connectors["naver"].http)
        res = {r.source: r for r in app.check()}
        self.assertEqual(res["kosis"].kind, "missing_key")
        self.assertEqual(res["law"].kind, "not_approved")
        self.assertFalse(res["datagokr"].ok)
        self.assertIn("활용신청", res["datagokr"].hint)


class TestSync(Base):
    def test_sync_then_skip_until_due(self):
        res = self.app.sync(log=lambda *a: None)
        status = {r["job"]: r["status"] for r in res}
        self.assertEqual(status["naver/shopping_categories"], "ok")
        self.assertEqual(status["law/watched_laws"], "ok")
        self.assertEqual(status["datagokr/file:3040720"], "ok")
        # 두 번째 실행: 성공한 작업은 주기가 안 됐으므로 건너뛰고, 실패한 작업만 다시 시도
        res2 = {r["job"]: r["status"] for r in self.app.sync(log=lambda *a: None)}
        for job, st in status.items():
            self.assertEqual(res2[job], "skipped" if st == "ok" else "error", job)

    def test_versioned_ingest_and_aggregate(self):
        ds = self.app.connectors["datagokr"]
        cfg = [d for d in ds.datasets if d["id"] == "3040720"][0]
        n1 = ds.sync_dataset(cfg)
        n2 = ds.sync_dataset(cfg)  # 새 버전 없으면 0
        self.assertEqual(n1, len(RELIEF_ROWS))  # 내용이 같은 행도 버리지 않음
        self.assertEqual(n2, 0)
        # 같은 행 묶음을 다시 넣으면(재게시된 버전) 중복으로 건너뜀
        self.assertEqual(self.app.store.insert_records("datagokr", "3040720", "again", RELIEF_ROWS), 0)
        hits = self.app.store.search("헬스장 불만")
        self.assertTrue(any(h["doc_type"] == "consumer_complaint" for h in hits))
        top = hits[0]["text"]
        self.assertIn("계약해제", top)
        series = self.app.store.get_series(dataset="agg:3040720", series_like="헬스장")
        self.assertEqual({s["series_key"]: s["value"] for s in series if s["period"] == "202606"}["헬스장 | 계약해제"], 5)

    def test_law_articles_and_watch(self):
        n = self.app.connectors["law"].sync_watched()
        self.assertGreater(n, 0)
        hits = self.app.store.search("청약철회 기간")
        self.assertIn("제17조", hits[0]["title"])
        self.assertIn("7일", hits[0]["text"])


class TestOnDemand(Base):
    def test_trend_cached_and_stored(self):
        from bizrag.knowledge import Knowledge
        k = Knowledge(self.app)
        r1 = k.naver_search_trend({"텀블러": ["텀블러", "보온병"]})
        before = len(self.router.calls)
        r2 = k.naver_search_trend({"텀블러": ["텀블러", "보온병"]})
        self.assertEqual(len(self.router.calls), before)  # 두 번째는 캐시
        self.assertEqual(r2.get("_cache"), "hit")
        self.assertIn("yoy_change_pct", r1["summary"]["텀블러"])
        s = k.get_series(dataset="datalab_search")
        self.assertEqual(s["count"], 1)

    def test_kosis_probe_and_refresh(self):
        from bizrag.knowledge import Knowledge
        k = Knowledge(self.app)
        tables = k.kosis_find_tables("온라인쇼핑")
        self.assertEqual(tables[0]["tblId"], "DT_1KE10041")
        self.assertEqual(self.app.store.search("온라인쇼핑 거래액")[0]["doc_type"], "stat_table")
        r = k.kosis_fetch_table("101", "DT_1KE10041")
        self.assertEqual(r["prdSe"], "M")  # Y 실패 → M 자동 탐색
        self.assertEqual(k.kosis_find_tables("없는통계"), [])
        # 조회했던 표는 월간 갱신 대상에 자동 포함
        self.assertGreater(self.app.connectors["kosis"].sync_tables(), 0)

    def test_kosis_uses_meta_for_levels_and_period(self):
        from bizrag.knowledge import Knowledge
        k = Knowledge(self.app)
        r = k.kosis_fetch_table("309", "DT_JP51", recent=3)
        self.assertEqual(r["prdSe"], "Y")  # 메타에서 최근 수록주기 선택 (2년보다 년)
        self.assertEqual(r["levels"], ["상거래현대화수준별", "지역별"])
        self.assertEqual(r["obj"], {"objL1": "ALL", "objL2": "ALL"})
        self.assertEqual(r["rows"], 1)
        # 일부 분류만 지정해도 나머지 단계는 ALL로 채움
        r2 = k.kosis_fetch_table("309", "DT_JP51", recent=3, obj={"objL1": "a1"})
        self.assertEqual(r2["obj"], {"objL1": "a1", "objL2": "ALL"})

    def test_shop_keywords_patent_worldbank(self):
        from bizrag.knowledge import Knowledge
        k = Knowledge(self.app)
        shop = k.naver_shopping_keywords("50000008", ["텀블러", "보온병"])
        self.assertEqual(set(shop["series"]), {"텀블러", "보온병"})
        # API HUB 호스트·헤더로 호출
        call = [c for c in self.router.calls if "/shopping/v1/category/keywords" in c[1]][0]
        self.assertTrue(call[1].startswith("https://naverapihub.apigw.ntruss.com/"))
        self.assertEqual(call[2]["headers"]["X-NCP-APIGW-API-KEY-ID"], "id")
        pat = k.patent_search("시약 관리")
        self.assertEqual(pat["top_applicants"][0][0], "주식회사 랩툴")
        self.assertEqual(self.app.store.search("시약 재고")[0]["source"], "kipris")
        # KIPRIS 키의 %2B는 한 번만 디코딩되어 전송
        sent = [c for c in self.router.calls if "getWordSearch" in c[1]][0][2]["params"]["ServiceKey"]
        self.assertEqual(sent, "k+1")
        wb = k.worldbank_indicator("SP.POP.TOTL", ["KOR"])
        self.assertEqual(wb["latest"]["KOR"][1], 51700000)

    def test_errors_are_returned_not_raised(self):
        from bizrag.knowledge import Knowledge
        del os.environ["NAVER_CLIENT_ID"]
        from bizrag.app import App
        app = App(self.tmp, store=self.app.store, http=self.app.connectors["naver"].http)
        out = Knowledge(app).naver_search_trend({"텀블러": ["텀블러"]})
        self.assertEqual(out["kind"], "missing_key")


class TestInbox(Base):
    def test_csv_cp949(self):
        d = self.tmp / "inbox" / "online_price"
        d.mkdir(parents=True)
        (d / "price_202609.csv").write_bytes("수집일,상품명,판매가격\n20260901,생수 2L,1200\n".encode("cp949"))
        n = self.app.connectors["inbox"].sync()
        self.assertEqual(n, 1)
        rec = self.app.store.find_records(source="inbox", contains="생수")
        self.assertEqual(rec[0]["row"]["판매가격"], "1200")
        self.assertTrue((self.tmp / "inbox" / "_done" / "online_price" / "price_202609.csv").exists())


class TestMcp(Base):
    def test_server_builds(self):
        from bizrag.knowledge import Knowledge
        from bizrag.mcp_server import build
        self.assertIsNotNone(build(Knowledge(self.app)))


if __name__ == "__main__":
    unittest.main()

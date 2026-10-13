"""MCP 서버: Claude Desktop/Claude Code 등 에이전트가 지식 DB를 도구로 쓰게 한다.

실행: python -m bizrag mcp
"""
from __future__ import annotations

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from .knowledge import Knowledge

INSTRUCTIONS = """사업 아이디어 평가용 지식 DB.
1) inventory로 무엇이 쌓였는지 본다.
2) search_knowledge(문서: 법령 조문, 특허, 통계표 카탈로그, 소비자 피해 요약, 한국은행 경제지표 요약)와
   get_series(시계열: 네이버 지수, KOSIS, 한국은행, World Bank)로 저장된 근거를 먼저 찾는다.
3) 부족할 때만 naver_*/kosis_*/bok_*/law_*/patent_search/worldbank_indicator로 새로 수집한다(결과는 DB에 누적).
주의: 네이버 지수는 같은 query_sig 안에서만 비교 가능한 상대값이다. 검색 관심도를 구매 의사로 단정하지 말 것.
한국은행 CSI·BSI·뉴스심리지수는 100 기준 심리지표이고, 기업경영분석은 업종 평균이라 개별 창업 수익성과 다를 수 있다.
답변에는 각 근거의 source·기간·수집시각을 밝힌다."""


def build(k: Knowledge | None = None):
    k = k or Knowledge()
    server = _Server("bizrag", instructions=INSTRUCTIONS)

    @server.tool()
    def inventory() -> dict:
        """DB에 저장된 문서·시계열·원자료 목록과 건수."""
        return k.inventory()

    @server.tool()
    def search_knowledge(query: str, sources: list[str] | None = None,
                         doc_types: list[str] | None = None, limit: int = 8) -> list[dict]:
        """저장된 문서 전문검색. sources 예: law, kipris, kosis, datagokr. doc_types 예: law_article, patent, stat_table, consumer_complaint."""
        return k.search_knowledge(query, sources, doc_types, limit)

    @server.tool()
    def get_series(dataset: str | None = None, series_contains: str | None = None,
                   source: str | None = None, query_sig: str | None = None) -> dict:
        """저장된 시계열 조회. dataset 예: datalab_search, shop_category, kosis:101/DT_xxx, bok:511Y002, wb:NY.GDP.MKTP.CD, agg:3040720.
        한국은행(bok:*)은 query_sig가 주기(M·Q·A·D, 뉴스심리지수 주간 평균은 W)."""
        return k.get_series(dataset, series_contains, source, query_sig)

    @server.tool()
    def find_records(source: str | None = None, dataset: str | None = None,
                     contains: str | None = None, limit: int = 50) -> list[dict]:
        """원자료 행 조회 (생필품 가격표, 피해구제·해외진출기업 원본 행, inbox CSV 등). contains는 행 안의 문자열."""
        return k.find_records(source, dataset, contains, limit)

    @server.tool()
    def naver_search_trend(keyword_groups: dict[str, list[str]], months: int = 36, time_unit: str = "month",
                           device: str = "", gender: str = "", ages: list[str] | None = None) -> dict:
        """네이버 검색어 트렌드 (최대 5그룹). 예: {"홈트": ["홈트레이닝","홈트"], "필라테스": ["필라테스"]}. gender m/f, device pc/mo, ages ["3","4"]=20대."""
        return k.naver_search_trend(keyword_groups, months, time_unit, device, gender, ages)

    @server.tool()
    def naver_shopping_keywords(category_id: str, keywords: list[str], months: int = 36) -> dict:
        """네이버 쇼핑 분야 안 키워드 클릭 추이 (최대 5개). category_id 예: 50000008 생활/건강."""
        return k.naver_shopping_keywords(category_id, keywords, months)

    @server.tool()
    def kosis_find_tables(query: str, limit: int = 20):
        """KOSIS 통계표 검색 (결과는 stat_table 문서로도 저장)."""
        return k.kosis_find_tables(query, limit)

    @server.tool()
    def kosis_fetch_table(org_id: str, tbl_id: str, prd_se: str = "", recent: int = 24,
                          obj: dict | None = None, itm_id: str = "ALL") -> dict:
        """KOSIS 통계표 최근 n시점 수집 → get_series로 조회. 한 번 조회한 표는 월간 자동 갱신 대상이 된다."""
        return k.kosis_fetch_table(org_id, tbl_id, prd_se, recent, obj, itm_id)

    @server.tool()
    def bok_find_tables(query: str, limit: int = 20):
        """한국은행 ECOS 통계표 이름 검색 (공백으로 나눈 단어가 모두 들어간 표). 예: "소비자동향", "기업경영분석 손익"."""
        return k.bok_find_tables(query, limit)

    @server.tool()
    def bok_table_items(stat_code: str):
        """ECOS 통계표의 분류·항목 코드와 주기별 수록기간 (bok_fetch_table의 items를 정할 때)."""
        return k.bok_table_items(stat_code)

    @server.tool()
    def bok_fetch_table(stat_code: str, cycle: str, items: list[str] | None = None, recent: int = 24) -> dict:
        """ECOS 통계표 최근 n시점 수집 → get_series(dataset="bok:<stat_code>")로 조회.
        cycle: A 연·Q 분기·M 월·D 일. items: 분류 1~4 코드, "?"=전체 (예: ["?", "99988"])."""
        return k.bok_fetch_table(stat_code, cycle, items, recent)

    @server.tool()
    def law_search(query: str):
        """법령 목록 검색 (법령명·시행일·소관부처)."""
        return k.law_search(query)

    @server.tool()
    def law_add(name: str) -> dict:
        """법령 전체 조문을 지식 DB에 적재하고 월간 개정 확인 대상으로 등록."""
        return k.law_add(name)

    @server.tool()
    def patent_search(word: str, rows: int = 30) -> dict:
        """KIPRIS 특허·실용신안 키워드 검색 (출원인·연도 분포 + 초록 문서 저장)."""
        return k.patent_search(word, rows)

    @server.tool()
    def worldbank_indicator(indicator: str, countries: list[str] | None = None) -> dict:
        """World Bank 지표. 예: indicator=NY.GDP.PCAP.CD, countries=["KOR","VNM"]."""
        return k.worldbank_indicator(indicator, countries)

    @server.tool()
    def source_status() -> list[dict]:
        """소스별 마지막 수집 시각과 다음 수집 예정."""
        return k.source_status()

    return server


def main():
    build().run()


if __name__ == "__main__":
    main()

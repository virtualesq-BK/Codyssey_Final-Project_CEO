from app.rag.web_search_retriever import CombinedRetriever, _focus, evidence_from_response


def test_evidence_groups_citations_by_url():
    data = {"content": [
        {"type": "text", "text": "검색해볼게요.", "citations": None},
        {"type": "server_tool_use", "input": {"query": "q"}},
        {"type": "text", "text": "국내 시장은 2025년 10조원 전망", "citations": [
            {"url": "https://www.a.com/x", "title": "A 기사", "cited_text": "국내 시장 규모는 2025년 10조원"}]},
        {"type": "text", "text": "연평균 8.5% 성장", "citations": [
            {"url": "https://www.a.com/x", "title": "A 기사", "cited_text": "연평균 8.5%"},
            {"url": "https://b.kr/y", "title": "B 통계", "cited_text": "8.5%"}]},
    ]}
    ev = evidence_from_response(data)
    assert [e.url for e in ev] == ["https://www.a.com/x", "https://b.kr/y"]
    assert ev[0].source == "웹검색 · a.com"
    assert "10조원 전망 / 연평균 8.5% 성장" in ev[0].content
    assert "원문:" in ev[0].content


def test_focus_uses_agent_prefix():
    focus, topic = _focus("CompetitorAgent 에듀테크 교사")
    assert "경쟁" in focus and topic == "에듀테크 교사"
    focus, topic = _focus("에듀테크 전국 시장 규모")
    assert "시장" in focus and topic == "에듀테크 전국 시장 규모"


async def test_combined_retriever_keeps_working_when_one_fails():
    from app.core.schemas import Evidence

    async def ok(q):
        return [Evidence(title="t", source="s", content="c")]

    async def boom(q):
        raise RuntimeError("x")

    out = await CombinedRetriever(ok, boom, None)("q")
    assert len(out) == 1

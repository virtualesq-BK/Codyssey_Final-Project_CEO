from app.rag.bizrag_bridge import _keywords, _short_query, relevant, to_evidence


def test_short_query_drops_agent_prefix_and_trims():
    q = _short_query("CustomerAgent 에듀테크 다문화 학급 담임교사가 주 사용자\n· 초등학교 다문화 학급 담임(1~6학년 담당) 한국어 능력이 다양한 학생 20~30명")
    assert not q.startswith("CustomerAgent")
    assert len(q.split()) <= 12


def test_relevance_needs_score_and_keyword():
    keys = _keywords("카페 창업 원가")
    assert not relevant({"score": 0.68, "title": "피해구제 — 할인회원권", "text": "계약해제 4건"}, keys)
    assert not relevant({"score": 0.2, "title": "카페 창업 비용", "text": ""}, keys)
    assert relevant({"score": 0.5, "title": "커피전문점 원가 구조", "text": "카페 원두 원가율"}, keys)


def test_to_evidence_reads_text_field():
    ev = to_evidence({"score": 0.5, "source": "kosis", "title": "다문화 학생 현황", "text": "초등 다문화 학생 11만 명", "url": "http://kosis.kr/x"})
    assert ev.content == "초등 다문화 학생 11만 명"
    assert ev.source == "RAG · kosis"

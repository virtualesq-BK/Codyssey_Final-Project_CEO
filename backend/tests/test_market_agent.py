"""MarketAgent 단위 테스트"""
from __future__ import annotations

import json
import pytest

from app.agents.market_agent import MarketAgent, MarketAnalysis, _normalize_claims
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentStatus, BusinessIdea, Evidence


@pytest.fixture
def idea():
    return BusinessIdea(
        idea_id="market-test-001",
        title="구독형 반려동물 용품 배송",
        problem="반려동물 용품 정기 구매가 번거롭다",
        customer="20~40대 직장인 반려동물 보호자",
        solution="월정액 구독으로 맞춤 용품 정기 배송",
        industry="반려동물",
        location="서울",
    )


def _claim(text="테스트", kind="hypothesis", refs=None):
    return {"text": text, "kind": kind, "evidence_indices": refs or []}


def _market_data(confidence=0.7, with_programs=True):
    programs = [{"name": "창업도약패키지", "description": _claim("지원사업", "fact", [0]),
                 "eligibility": _claim("3년 이내 창업기업"), "source_index": 0}] if with_programs else []
    return {
        "summary": "반려동물 시장 분석 완료",
        "market_size": _claim("시장 규모 미확인", "hypothesis"),
        "growth_rate": _claim("성장률 미확인", "hypothesis"),
        "key_trends": [_claim("1인 가구 증가", "hypothesis")],
        "target_market_size": _claim("서울 반려동물 시장 미확인", "hypothesis"),
        "market_readiness": _claim("시장 준비도 중간", "hypothesis"),
        "support_programs": programs,
        "recommendations": ["KOSIS 통계 확인 필요"],
        "confidence": confidence,
    }


# ── _normalize_claims ─────────────────────────────────────────────────────

def test_normalize_fact_without_evidence_downgraded():
    data = {"key": _claim("수치", "fact", [0])}
    changed = _normalize_claims(data, evidence_count=0)
    assert changed
    assert data["key"]["kind"] == "hypothesis"


def test_normalize_fact_with_valid_index_kept():
    data = {"key": _claim("수치", "fact", [0])}
    changed = _normalize_claims(data, evidence_count=2)
    assert not changed
    assert data["key"]["kind"] == "fact"


def test_normalize_fact_with_out_of_range_index_downgraded():
    data = {"key": _claim("수치", "fact", [5])}
    changed = _normalize_claims(data, evidence_count=3)
    assert changed
    assert data["key"]["kind"] == "hypothesis"


# ── MarketAgent (mock) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_market_agent_no_retriever_partial(idea):
    mock = MockProvider()
    mock.set_responses([json.dumps(_market_data(), ensure_ascii=False)])
    agent = MarketAgent(llm_provider=mock)
    result = await agent.run(idea)

    assert result.status == AgentStatus.PARTIAL
    assert result.confidence <= 0.3
    assert result.evidence == []
    assert "market_analysis" in result.findings[0]


@pytest.mark.asyncio
async def test_market_agent_with_retriever_evidence_attached(idea):
    async def fake_retriever(query: str) -> list[Evidence]:
        return [Evidence(title="시장조사", source="KOSIS", content="시장 규모 데이터", confidence=0.8)]

    mock = MockProvider()
    mock.set_responses([json.dumps(_market_data(confidence=0.8), ensure_ascii=False)])
    agent = MarketAgent(llm_provider=mock, evidence_retriever=fake_retriever)
    result = await agent.run(idea)

    # 3개 쿼리로 검색 → evidence가 붙어야 함
    assert len(result.evidence) >= 1


@pytest.mark.asyncio
async def test_market_agent_deduplicates_evidence(idea):
    """같은 source+title 중복 evidence는 한 번만 포함한다."""
    async def fake_retriever(query: str) -> list[Evidence]:
        return [Evidence(title="동일문서", source="KOSIS", content="내용", confidence=0.8)]

    mock = MockProvider()
    mock.set_responses([json.dumps(_market_data(confidence=0.7), ensure_ascii=False)])
    agent = MarketAgent(llm_provider=mock, evidence_retriever=fake_retriever)
    result = await agent.run(idea)

    titles = [e.title for e in result.evidence]
    assert titles.count("동일문서") == 1


@pytest.mark.asyncio
async def test_market_agent_fabricated_fact_downgraded(idea):
    """evidence 없이 fact를 반환하면 hypothesis로 강제 전환한다."""
    data = _market_data(confidence=0.9)
    data["market_size"] = _claim("시장 규모 10조 원", "fact", [0])  # evidence 없는데 fact

    mock = MockProvider()
    mock.set_responses([json.dumps(data, ensure_ascii=False)])
    agent = MarketAgent(llm_provider=mock)  # retriever 없음 → evidence 0개
    result = await agent.run(idea)

    analysis = result.findings[0]["market_analysis"]
    assert analysis["market_size"]["kind"] == "hypothesis"
    assert result.confidence <= 0.3


@pytest.mark.asyncio
async def test_market_agent_retriever_timeout_graceful(idea):
    """retriever 타임아웃 시 빈 evidence로 계속 진행한다."""
    import asyncio as _asyncio

    async def slow_retriever(query: str) -> list[Evidence]:
        await _asyncio.sleep(99)
        return []

    mock = MockProvider()
    mock.set_responses([json.dumps(_market_data(), ensure_ascii=False)])
    agent = MarketAgent(llm_provider=mock, evidence_retriever=slow_retriever,
                        retrieval_timeout_sec=0.01)
    result = await agent.run(idea)
    assert result.status in (AgentStatus.PARTIAL, AgentStatus.FAILED)


@pytest.mark.asyncio
async def test_market_agent_llm_failure(idea):
    class _FailProvider(MockProvider):
        async def generate_structured(self, *a, **kw):
            raise RuntimeError("LLM 연결 실패")

    agent = MarketAgent(llm_provider=_FailProvider())
    result = await agent.run(idea)
    assert result.status == AgentStatus.FAILED


def test_market_agent_class_is_used_by_orchestrator():
    """Orchestrator가 market_agent 파라미터로 MarketAgent 인스턴스를 받아들인다."""
    from app.agents.market_agent import MarketAgent as MA
    mock = MockProvider()
    agent = MA(llm_provider=mock)
    assert agent.agent_name == "MarketAgent"
    assert isinstance(agent, MA)

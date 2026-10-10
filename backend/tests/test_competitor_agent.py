"""CompetitorAgent 단위 테스트"""
from __future__ import annotations

import json
import pytest

from app.agents.business_agents import CompetitionAnalysis, CompetitorAgent
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentStatus, BusinessIdea


@pytest.fixture
def idea():
    return BusinessIdea(
        idea_id="comp-test-001",
        title="구독형 반려동물 용품 배송",
        problem="반려동물 용품 정기 구매가 번거롭다",
        customer="20~40대 직장인 반려동물 보호자",
        solution="월정액 구독으로 맞춤 용품 정기 배송",
        industry="반려동물",
        location="서울",
    )


def _make_mock_response(
    direct: list[dict] | None = None,
    indirect: list[dict] | None = None,
    confidence: float = 0.7,
) -> str:
    """MockProvider에 주입할 CompetitionAnalysis JSON 생성."""
    claim_fact = {"text": "테스트", "kind": "fact", "evidence_indices": [0]}
    claim_hyp = {"text": "테스트 가설", "kind": "hypothesis", "evidence_indices": []}

    competitor = {
        "name": "경쟁사A",
        "description": claim_hyp,
        "strengths": [claim_hyp],
        "weaknesses": [claim_hyp],
        "target_customer": claim_hyp,
    }

    data = {
        "summary": "경쟁 분석 완료",
        "direct_competitors": direct if direct is not None else [competitor],
        "indirect_competitors": indirect if indirect is not None else [],
        "differentiation": [claim_hyp],
        "entry_barriers": [claim_hyp],
        "competitive_position": claim_hyp,
        "recommendations": ["경쟁사 직접 조사 필요"],
        "confidence": confidence,
    }
    return json.dumps(data, ensure_ascii=False)


@pytest.mark.asyncio
async def test_competitor_agent_success(idea):
    """evidence 없이도 PARTIAL 상태로 결과를 반환한다."""
    mock = MockProvider()
    mock.set_responses([_make_mock_response()])

    agent = CompetitorAgent(llm_provider=mock)
    result = await agent.run(idea)

    assert result.agent_name == "CompetitorAgent"
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert result.confidence > 0
    assert len(result.findings) == 1
    assert "competition_analysis" in result.findings[0]


@pytest.mark.asyncio
async def test_competitor_agent_no_evidence_lowers_confidence(idea):
    """evidence_retriever 없으면 confidence가 0.3 이하로 제한된다."""
    mock = MockProvider()
    mock.set_responses([_make_mock_response(confidence=0.9)])

    agent = CompetitorAgent(llm_provider=mock, evidence_retriever=None)
    result = await agent.run(idea)

    assert result.confidence <= 0.3
    assert result.status == AgentStatus.PARTIAL


@pytest.mark.asyncio
async def test_competitor_agent_with_evidence_retriever(idea):
    """evidence_retriever 제공 시 evidence가 결과에 포함된다."""
    from app.core.schemas import Evidence

    async def fake_retriever(query: str) -> list[Evidence]:
        return [Evidence(title="테스트 출처", source="test", content="경쟁사 정보", confidence=0.8)]

    mock = MockProvider()
    mock.set_responses([_make_mock_response(confidence=0.7)])

    agent = CompetitorAgent(llm_provider=mock, evidence_retriever=fake_retriever)
    result = await agent.run(idea)

    assert len(result.evidence) == 1
    assert result.evidence[0].source == "test"


@pytest.mark.asyncio
async def test_competitor_agent_empty_direct_competitors(idea):
    """직접 경쟁사가 없어도 결과 구조가 유효하다."""
    mock = MockProvider()
    mock.set_responses([_make_mock_response(direct=[], indirect=[])])

    agent = CompetitorAgent(llm_provider=mock)
    result = await agent.run(idea)

    analysis = result.findings[0]["competition_analysis"]
    assert analysis["direct_competitors"] == []


@pytest.mark.asyncio
async def test_competitor_agent_fabricated_fact_downgraded(idea):
    """근거 없는 fact claim이 hypothesis로 다운그레이드된다."""
    claim_fabricated_fact = {"text": "시장점유율 30%", "kind": "fact", "evidence_indices": [99]}
    competitor = {
        "name": "경쟁사B",
        "description": claim_fabricated_fact,
        "strengths": [claim_fabricated_fact],
        "weaknesses": [{"text": "약점", "kind": "hypothesis", "evidence_indices": []}],
        "target_customer": {"text": "고객", "kind": "hypothesis", "evidence_indices": []},
    }
    data = {
        "summary": "테스트",
        "direct_competitors": [competitor],
        "indirect_competitors": [],
        "differentiation": [{"text": "차별화", "kind": "hypothesis", "evidence_indices": []}],
        "entry_barriers": [{"text": "진입장벽", "kind": "hypothesis", "evidence_indices": []}],
        "competitive_position": {"text": "포지션", "kind": "hypothesis", "evidence_indices": []},
        "recommendations": ["테스트"],
        "confidence": 0.8,
    }
    mock = MockProvider()
    mock.set_responses([json.dumps(data, ensure_ascii=False)])

    agent = CompetitorAgent(llm_provider=mock)
    result = await agent.run(idea)

    analysis = result.findings[0]["competition_analysis"]
    desc = analysis["direct_competitors"][0]["description"]
    assert desc["kind"] == "hypothesis"


@pytest.mark.asyncio
async def test_competitor_agent_llm_failure(idea):
    """LLM 실패 시 FAILED 상태로 반환된다 (retry 후)."""
    class _AlwaysFailProvider(MockProvider):
        async def generate_structured(self, *a, **kw):
            raise RuntimeError("LLM 연결 실패")

    agent = CompetitorAgent(llm_provider=_AlwaysFailProvider())
    result = await agent.run(idea)

    assert result.status == AgentStatus.FAILED


def test_competitor_agent_importable_from_dummy():
    """dummy_agents re-export 경로로도 import 가능해야 한다."""
    from app.agents.dummy_agents import CompetitorAgent as CA
    assert CA is CompetitorAgent

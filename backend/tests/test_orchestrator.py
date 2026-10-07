"""
Orchestrator workflow tests – LLM 호출 없음
"""
import pytest

from app.agents.orchestrator import Orchestrator
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentStatus, BusinessIdea


def make_idea() -> BusinessIdea:
    return BusinessIdea(
        idea_id="orch-001",
        title="배달 세탁 서비스",
        problem="바쁜 직장인이 세탁소 방문 시간 없음",
        customer="25-40대 직장인",
        solution="앱으로 픽업·배달 세탁 서비스",
        industry="생활서비스",
        location="서울",
    )


@pytest.mark.asyncio
async def test_workflow_completes():
    mock_llm = MockProvider()
    # Decision Agent가 JSON 응답 반환하도록 설정
    mock_llm.set_responses([
        '{"summary":"테스트","strengths":[],"weaknesses":[],"opportunities":[],'
        '"risks":[],"financial_summary":"미확정","validation_items":[],'
        '"action_plan":[],"decision":"VALIDATE_MORE","confidence":0.5}'
    ])
    orchestrator = Orchestrator(llm_provider=mock_llm)
    result = await orchestrator.run(make_idea())

    assert result.idea_id == "orch-001"
    assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
    assert len(result.agent_results) == 6


@pytest.mark.asyncio
async def test_workflow_has_decision_result():
    mock_llm = MockProvider()
    mock_llm.set_responses([
        '{"summary":"결론","strengths":["장점1"],"weaknesses":[],"opportunities":[],'
        '"risks":[],"financial_summary":"미확정","validation_items":[],'
        '"action_plan":["1단계"],"decision":"GO","confidence":0.7}'
    ])
    orchestrator = Orchestrator(llm_provider=mock_llm)
    result = await orchestrator.run(make_idea())
    assert result.decision_result is not None


@pytest.mark.asyncio
async def test_aggregate_status_partial():
    """일부 Agent 실패 시 PARTIAL 상태"""
    from app.core.schemas import AgentResult

    results = {
        "A": AgentResult(agent_name="A", status=AgentStatus.SUCCESS, summary="ok", confidence=0.8),
        "B": AgentResult.failed("B", "timeout"),
    }
    status = Orchestrator._aggregate_status(results)
    assert status == AgentStatus.PARTIAL


@pytest.mark.asyncio
async def test_aggregate_status_all_success():
    from app.core.schemas import AgentResult

    results = {
        "A": AgentResult(agent_name="A", status=AgentStatus.SUCCESS, summary="ok", confidence=0.8),
        "B": AgentResult(agent_name="B", status=AgentStatus.SUCCESS, summary="ok", confidence=0.6),
    }
    status = Orchestrator._aggregate_status(results)
    assert status == AgentStatus.SUCCESS

"""
Decision Agent tests – LLM mock 사용
"""
import pytest

from app.agents.decision_agent import DecisionAgent
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea, Decision


def make_idea() -> BusinessIdea:
    return BusinessIdea(
        idea_id="dec-001",
        title="구독 도시락 서비스",
        problem="직장인 점심 선택 피로",
        customer="30대 직장인",
        solution="맞춤 도시락 정기 배송",
        industry="식음료",
    )


def make_agent_results() -> dict[str, AgentResult]:
    return {
        "MarketAgent": AgentResult(
            agent_name="MarketAgent",
            status=AgentStatus.SUCCESS,
            summary="시장 분석 완료",
            confidence=0.6,
        ),
        "CustomerAgent": AgentResult(
            agent_name="CustomerAgent",
            status=AgentStatus.SUCCESS,
            summary="고객 분석 완료",
            confidence=0.5,
        ),
    }


@pytest.mark.asyncio
async def test_decision_go():
    mock = MockProvider()
    mock.set_responses([
        '{"summary":"유망한 아이디어","strengths":["수요 확인"],'
        '"weaknesses":["경쟁 심화"],"opportunities":["시장 성장"],'
        '"risks":["단가 압박"],"financial_summary":"근거 부족",'
        '"validation_items":["파일럿 필요"],"action_plan":["1단계 실행"],'
        '"decision":"GO","confidence":0.75}'
    ])
    agent = DecisionAgent(llm_provider=mock, agent_results=make_agent_results())
    result = await agent.decide(make_idea())

    assert result.decision == Decision.GO
    assert result.confidence == pytest.approx(0.75)
    assert len(result.strengths) > 0


@pytest.mark.asyncio
async def test_decision_fallback_on_invalid_json():
    mock = MockProvider()
    mock.set_responses(["이것은 JSON이 아닙니다"])
    agent = DecisionAgent(llm_provider=mock, agent_results=make_agent_results())
    result = await agent.decide(make_idea())

    # fallback은 VALIDATE_MORE
    assert result.decision == Decision.VALIDATE_MORE
    assert result.disclaimer != ""


@pytest.mark.asyncio
async def test_decision_structured_output():
    mock = MockProvider()
    mock.set_responses([
        '{"summary":"요약","strengths":[],"weaknesses":[],"opportunities":[],'
        '"risks":[],"financial_summary":"미확정","validation_items":[],'
        '"action_plan":[],"decision":"PIVOT","confidence":0.4}'
    ])
    agent = DecisionAgent(llm_provider=mock, agent_results=make_agent_results())
    result = await agent.decide(make_idea())

    assert result.decision == Decision.PIVOT


@pytest.mark.asyncio
async def test_agent_run_returns_agent_result():
    mock = MockProvider()
    mock.set_responses([
        '{"summary":"요약","strengths":[],"weaknesses":[],"opportunities":[],'
        '"risks":[],"financial_summary":"미확정","validation_items":[],'
        '"action_plan":[],"decision":"STOP","confidence":0.2}'
    ])
    agent = DecisionAgent(llm_provider=mock, agent_results=make_agent_results())
    result = await agent.run(make_idea())

    assert result.agent_name == "DecisionAgent"
    assert result.status == AgentStatus.SUCCESS

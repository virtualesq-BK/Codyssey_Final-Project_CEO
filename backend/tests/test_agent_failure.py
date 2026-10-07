"""
Agent failure handling tests
"""
import pytest

from app.core.base_agent import BaseAgent
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea


class AlwaysFailAgent(BaseAgent):
    MAX_RETRIES = 1

    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        raise RuntimeError("의도적 실패")


class FailThenSucceedAgent(BaseAgent):
    MAX_RETRIES = 1
    _call_count = 0

    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        FailThenSucceedAgent._call_count += 1
        if FailThenSucceedAgent._call_count < 2:
            raise RuntimeError("첫 번째 실패")
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary="재시도 성공",
            confidence=0.7,
        )


def make_idea() -> BusinessIdea:
    return BusinessIdea(
        idea_id="fail-001",
        title="테스트",
        problem="테스트 문제",
        customer="테스트 고객",
        solution="테스트 솔루션",
        industry="IT",
    )


@pytest.mark.asyncio
async def test_always_fail_returns_failed_result():
    agent = AlwaysFailAgent(llm_provider=MockProvider())
    result = await agent.run(make_idea())
    assert result.status == AgentStatus.FAILED
    assert "의도적 실패" in result.error_message


@pytest.mark.asyncio
async def test_retry_succeeds():
    FailThenSucceedAgent._call_count = 0
    agent = FailThenSucceedAgent(llm_provider=MockProvider())
    result = await agent.run(make_idea())
    assert result.status == AgentStatus.SUCCESS


@pytest.mark.asyncio
async def test_orchestrator_partial_on_agent_failure():
    """한 Agent 실패해도 workflow 전체가 PARTIAL로 완료"""
    from app.agents.orchestrator import Orchestrator

    class BrokenAgent(BaseAgent):
        MAX_RETRIES = 0

        async def _execute(self, idea: BusinessIdea) -> AgentResult:
            raise RuntimeError("broken")

    mock = MockProvider()
    mock.set_responses([
        '{"summary":"ok","strengths":[],"weaknesses":[],"opportunities":[],'
        '"risks":[],"financial_summary":"미확정","validation_items":[],'
        '"action_plan":[],"decision":"VALIDATE_MORE","confidence":0.5}'
    ])
    orchestrator = Orchestrator(
        market_agent=BrokenAgent(llm_provider=mock),
        llm_provider=mock,
    )
    result = await orchestrator.run(make_idea())
    assert result.status in (AgentStatus.PARTIAL, AgentStatus.SUCCESS)
    assert result.agent_results["MarketAgent"].status == AgentStatus.FAILED

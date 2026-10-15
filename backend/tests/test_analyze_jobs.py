"""상세분석 백그라운드 작업 — 에이전트를 가짜로 바꿔 진행 기록과 결과를 확인"""
import asyncio

import pytest

from app.api import analyze_jobs
from app.api.routes import AnalyzeRequest
from app.core.schemas import AgentResult, AgentStatus


class FakeAgent:
    def __init__(self, name):
        self.name = name

    async def run(self, idea):
        await asyncio.sleep(0)
        return AgentResult(agent_name=self.name, status=AgentStatus.PARTIAL, summary=f"{self.name} 요약 / 근거 부족")


class FakeDecision:
    async def decide(self, idea):
        return None


class FakeOrchestrator:
    def __init__(self, **_):
        self.agents = {n: FakeAgent(n) for n in analyze_jobs.STAGES if n != "DecisionAgent"}
        self._decision_agent = FakeDecision()

    async def run(self, idea):
        from app.core.schemas import WorkflowResult

        out = WorkflowResult(idea_id=idea.idea_id, status=AgentStatus.PARTIAL)
        for n, a in self.agents.items():
            out.agent_results[n] = await a.run(idea)
        await self._decision_agent.decide(idea)
        return out


@pytest.mark.asyncio
async def test_job_records_each_stage_and_result(monkeypatch):
    monkeypatch.setattr(analyze_jobs, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(analyze_jobs, "get_adapters", lambda: None)
    monkeypatch.setattr(analyze_jobs, "build_external_retriever", lambda: None)
    req = AnalyzeRequest(title="t", problem="p", customer="c", solution="s", industry="i")
    created = await analyze_jobs.start_job(req)
    for _ in range(50):
        job = await analyze_jobs.get_job(created.job_id)
        if job.status != "running":
            break
        await asyncio.sleep(0.01)
    assert job.status == "done"
    assert job.result is not None
    assert job.stages["MarketAgent"].state == "done"
    assert job.stages["MarketAgent"].status == "partial"
    assert job.stages["MarketAgent"].summary == "MarketAgent 요약"
    assert job.stages["DecisionAgent"].state == "done"


@pytest.mark.asyncio
async def test_unknown_job_is_404():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        await analyze_jobs.get_job("nope")
    assert e.value.status_code == 404

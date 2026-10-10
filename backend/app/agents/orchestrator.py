"""
Orchestrator Agent
AI 분석 workflow 전체를 관리
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Type

from app.core.base_agent import BaseAgent
from app.core.llm_provider import LLMProvider
from app.core.schemas import (
    AgentResult,
    AgentStatus,
    BusinessIdea,
    TokenUsage,
    WorkflowResult,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Workflow:
      병렬: MarketAgent / CustomerAgent / CompetitorAgent
      순차: BusinessModelAgent
      병렬: FinancialAgent / RiskAgent
      순차: DecisionAgent
    """

    def __init__(
        self,
        market_agent: Optional[BaseAgent] = None,
        customer_agent: Optional[BaseAgent] = None,
        competitor_agent: Optional[BaseAgent] = None,
        business_model_agent: Optional[BaseAgent] = None,
        financial_agent: Optional[BaseAgent] = None,
        risk_agent: Optional[BaseAgent] = None,
        decision_agent: Optional[object] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        # 기본값: Dummy Agents (팀원 구현 전까지)
        from app.agents.dummy_agents import (
            BusinessModelAgent,
            CompetitorAgent,
            CustomerAgent,
            MarketAgent,
        )
        from app.agents.decision_agent import DecisionAgent
        from app.agents.financial_agent import FinancialAgent
        from app.agents.risk_agent import RiskAgent

        self.agents: dict[str, BaseAgent] = {
            "MarketAgent": market_agent or MarketAgent(llm_provider=llm_provider),
            "CustomerAgent": customer_agent or CustomerAgent(llm_provider=llm_provider),
            "CompetitorAgent": competitor_agent or CompetitorAgent(llm_provider=llm_provider),
            "BusinessModelAgent": business_model_agent or BusinessModelAgent(llm_provider=llm_provider),
            "FinancialAgent": financial_agent or FinancialAgent(llm_provider=llm_provider),
            "RiskAgent": risk_agent or RiskAgent(llm_provider=llm_provider),
        }
        self._decision_agent: object = decision_agent or DecisionAgent(llm_provider=llm_provider)

    async def run(self, idea: BusinessIdea) -> WorkflowResult:
        t0 = time.monotonic()
        result = WorkflowResult(idea_id=idea.idea_id, status=AgentStatus.RUNNING)
        logger.info("[Orchestrator] workflow 시작 idea_id=%s", idea.idea_id)

        # ── Phase 1: 병렬 (Market / Customer / Competitor) ──────────────
        phase1_names = ["MarketAgent", "CustomerAgent", "CompetitorAgent"]
        phase1_results = await self._run_parallel(phase1_names, idea)
        result.agent_results.update(phase1_results)

        # ── Phase 2: BusinessModelAgent (Phase1 의존) ────────────────────
        from app.agents.business_agents import BusinessModelAgent
        business_agent = self.agents["BusinessModelAgent"]
        if isinstance(business_agent, BusinessModelAgent):
            business_agent.set_agent_results(phase1_results)
        bm_result = await self._run_one("BusinessModelAgent", idea)
        result.agent_results["BusinessModelAgent"] = bm_result

        # ── Phase 3: 병렬 (Financial / Risk) ────────────────────────────
        phase3_names = ["FinancialAgent", "RiskAgent"]
        phase3_results = await self._run_parallel(phase3_names, idea)
        result.agent_results.update(phase3_results)

        # ── Phase 4: Decision Agent ──────────────────────────────────────
        from app.agents.decision_agent import DecisionAgent
        if isinstance(self._decision_agent, DecisionAgent):
            self._decision_agent.set_agent_results(result.agent_results)
        try:
            decision_result = await self._decision_agent.decide(idea)  # type: ignore[union-attr]
            result.decision_result = decision_result
        except Exception as exc:
            logger.error("[Orchestrator] DecisionAgent 실패: %s", exc)

        # ── 상태 집계 ────────────────────────────────────────────────────
        result.status = self._aggregate_status(result.agent_results)
        result.total_execution_time_ms = int((time.monotonic() - t0) * 1000)

        # Token usage 수집
        for agent in self.agents.values():
            result.token_usages.extend(agent.get_token_usages())

        logger.info(
            "[Orchestrator] workflow 완료 status=%s time=%dms",
            result.status,
            result.total_execution_time_ms,
        )
        return result

    async def _run_one(self, name: str, idea: BusinessIdea) -> AgentResult:
        agent = self.agents.get(name)
        if agent is None:
            return AgentResult.skipped(name, "Agent 미등록")
        try:
            return await agent.run(idea)
        except Exception as exc:
            logger.error("[Orchestrator] %s 예외: %s", name, exc)
            return AgentResult.failed(name, str(exc))

    async def _run_parallel(
        self, names: list[str], idea: BusinessIdea
    ) -> dict[str, AgentResult]:
        tasks = {name: self._run_one(name, idea) for name in names}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        out: dict[str, AgentResult] = {}
        for name, res in zip(tasks.keys(), results):
            if isinstance(res, Exception):
                out[name] = AgentResult.failed(name, str(res))
            elif isinstance(res, AgentResult):
                out[name] = res
            else:
                out[name] = AgentResult.failed(name, "Unexpected result type")
        return out

    @staticmethod
    def _aggregate_status(agent_results: dict[str, AgentResult]) -> AgentStatus:
        statuses = {r.status for r in agent_results.values()}
        if not statuses:
            return AgentStatus.FAILED
        if all(s == AgentStatus.SUCCESS for s in statuses):
            return AgentStatus.SUCCESS
        if all(s == AgentStatus.FAILED for s in statuses):
            return AgentStatus.FAILED
        return AgentStatus.PARTIAL

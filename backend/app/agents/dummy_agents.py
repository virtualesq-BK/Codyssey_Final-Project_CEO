"""
Dummy Agents – 1주차 E2E 연결용
실제 LLM 호출 없이 구조화된 AgentResult 반환
팀원의 실제 Agent로 교체 예정
"""
from __future__ import annotations

from app.core.base_agent import BaseAgent
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea, Evidence


def _dummy_evidence(title: str, agent: str) -> Evidence:
    return Evidence(
        title=title,
        source=f"{agent} Dummy",
        content=f"{title} (더미 데이터 – 실제 분석으로 교체 예정)",
        confidence=0.5,
    )


class MarketAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary=f"{idea.industry} 시장 분석 완료 (더미)",
            findings=[
                {"market_size": "미확인 – 실제 데이터 필요"},
                {"growth_rate": "미확인"},
                {"key_trends": ["디지털 전환", "1인 가구 증가"]},
            ],
            evidence=[_dummy_evidence("시장 규모 추정", "MarketAgent")],
            recommendations=["시장 검증 후 진입 규모 결정 필요"],
            confidence=0.4,
        )


class CompetitorAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary=f"{idea.industry} 경쟁 분석 완료 (더미)",
            findings=[
                {"direct_competitors": ["경쟁사 A", "경쟁사 B"]},
                {"differentiation": idea.solution},
            ],
            evidence=[_dummy_evidence("경쟁사 비교 필요", "CompetitorAgent")],
            recommendations=["차별화 포인트 명확화 필요"],
            confidence=0.4,
        )


# Orchestrator와 기존 호출 코드의 가져오기 경로를 유지한다.
from app.agents.business_agents import CustomerAgent, BusinessModelAgent

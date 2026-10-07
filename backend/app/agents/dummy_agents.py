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


class CustomerAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary=f"'{idea.customer}' 고객 분석 완료 (더미)",
            findings=[
                {"target_segment": idea.customer},
                {"pain_points": ["편의성 부족", "비용 문제"]},
                {"willingness_to_pay": "미확인"},
            ],
            evidence=[_dummy_evidence("고객 인터뷰 필요", "CustomerAgent")],
            recommendations=["고객 인터뷰 최소 10건 수행 권장"],
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


class BusinessModelAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary="비즈니스 모델 분석 완료 (더미)",
            findings=[
                {"revenue_model": "미확정"},
                {"value_proposition": idea.solution},
                {"channels": ["온라인", "오프라인"]},
            ],
            evidence=[_dummy_evidence("BM 검증 필요", "BusinessModelAgent")],
            recommendations=["수익 모델 명확화 후 단가 계산 필요"],
            confidence=0.4,
        )


class FinancialAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary="재무 분석 완료 (더미)",
            findings=[
                {"initial_investment": "미확정"},
                {"break_even": "미확정"},
                {"monthly_burn": "미확정"},
            ],
            evidence=[_dummy_evidence("재무 모델링 필요", "FinancialAgent")],
            recommendations=["초기 투자비용과 월 운영비 추정 필요"],
            confidence=0.3,
        )


class RiskAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary="리스크 분석 완료 (더미)",
            findings=[
                {"market_risk": "시장 반응 불확실성"},
                {"regulatory_risk": "규제 리스크 미확인"},
                {"execution_risk": "팀 역량 확인 필요"},
            ],
            evidence=[_dummy_evidence("리스크 상세 분석 필요", "RiskAgent")],
            recommendations=["핵심 리스크 Top3 도출 후 대응책 수립"],
            confidence=0.4,
        )

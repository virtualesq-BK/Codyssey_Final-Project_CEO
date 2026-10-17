"""
Risk evidence interface – RAG(B팀원)와 Risk Agent 사이의 경계
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.schemas import BusinessIdea, Evidence
from app.risk.taxonomy import RiskCategory


@runtime_checkable
class RiskEvidenceProvider(Protocol):
    async def get_evidence(self, idea: BusinessIdea, category: RiskCategory) -> list[Evidence]:
        """category 에 해당하는 출처 있는 근거를 반환"""
        ...


class NullRiskEvidenceProvider:
    """RAG 연동 전 기본값 – 근거를 제공하지 않는다"""

    async def get_evidence(self, idea: BusinessIdea, category: RiskCategory) -> list[Evidence]:
        return []

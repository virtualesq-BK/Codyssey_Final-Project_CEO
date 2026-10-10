"""
Benchmark interface – RAG(B팀원)와 Financial Agent 사이의 경계

RAG 는 산업 평균·가격·CAC·margin 등 외부 가정만 제공하고,
실제 계산은 항상 Python calculator 가 수행한다.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.core.schemas import BusinessIdea, Evidence


class Benchmark(BaseModel):
    variable: str  # FinancialInputs 의 필드명
    value: float
    evidence: Evidence


@runtime_checkable
class BenchmarkProvider(Protocol):
    async def get_benchmarks(self, idea: BusinessIdea, variables: list[str]) -> list[Benchmark]:
        """부족한 재무 변수(variables)에 대한 benchmark 를 출처와 함께 반환"""
        ...


class NullBenchmarkProvider:
    """RAG 연동 전 기본값 – benchmark 를 제공하지 않는다"""

    async def get_benchmarks(self, idea: BusinessIdea, variables: list[str]) -> list[Benchmark]:
        return []

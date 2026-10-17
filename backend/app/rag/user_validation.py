"""
창업가 검증 근거 (가설 검증 기록 → 상세분석 근거)

창업가가 직접 검증한 결과(인터뷰·설문·사전예약·MVP 시범·판매 테스트·전문가 자문·데이터 분석 등)를
에이전트가 인용할 수 있는 Evidence로 바꿔, 웹검색·RAG와 같은 자리에 끼워 넣는다.
- 에이전트·오케스트레이터(A 소유)는 그대로 두고, 상세분석 작업(analyze_jobs)에서 retriever를 합친다
- 출처는 항상 '창업가 검증'으로 표시한다 (자가 보고라 외부 자료와 구분되게)
- 반증된 가설도 그대로 넘긴다 — 점수가 내려갈 수 있어야 좋은 결과만 넣는 게임이 안 된다
- 방법·표본 수에 따라 confidence를 달리해, 지인 몇 명 인터뷰와 실제 구매 행동을 같은 무게로 두지 않는다
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.schemas import BusinessIdea, Evidence
from app.risk.taxonomy import RiskCategory

ValidationArea = Literal["MarketAgent", "CustomerAgent", "CompetitorAgent", "BusinessModelAgent", "FinancialAgent", "RiskAgent"]
ValidationResult = Literal["supported", "refuted", "unclear"]

RESULT_TEXT = {
    "supported": "검증됨 — 가설이 맞는 것으로 확인됨",
    "refuted": "반증됨 — 가설이 틀린 것으로 확인됨",
    "unclear": "애매함 — 결론을 내리기 어려움",
}

# 실제 행동(가입·결제)을 본 검증일수록 무겁다. 목록에 없는 방법은 기본값
METHOD_WEIGHT = {
    "고객 인터뷰": 0.45,
    "설문조사": 0.5,
    "랜딩페이지·사전예약": 0.65,
    "MVP 시범 운영": 0.65,
    "판매 테스트": 0.7,
    "전문가 자문": 0.4,
    "데이터 분석": 0.55,
}
DEFAULT_WEIGHT = 0.4

# 재무 검증(가격·비용)은 재무 에이전트가 근거 검색을 하지 않아 수익 구조 쪽 근거로 넘긴다
AREA_ROUTE = {"FinancialAgent": "BusinessModelAgent"}
SEARCHING_AGENTS = ("CustomerAgent", "CompetitorAgent", "BusinessModelAgent")


class ValidationInput(BaseModel):
    id: str = Field(default="", max_length=80)
    hypothesis: str = Field(min_length=1, max_length=400)
    area: ValidationArea = "CustomerAgent"
    result: ValidationResult
    method: str = Field(default="", max_length=40)
    sample_size: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    target: str = Field(default="", max_length=120)
    metric: str = Field(default="", max_length=400)
    note: str = Field(default="", max_length=2000)
    done_at: str = Field(default="", max_length=20)
    updated_at: str = Field(default="", max_length=40)


def strength(v: ValidationInput) -> float:
    """방법·표본 수로 본 근거 무게 (0.2~0.8). 자가 보고라 외부 통계보다 높게 두지 않는다"""
    w = METHOD_WEIGHT.get(v.method, DEFAULT_WEIGHT)
    n = v.sample_size
    if n is not None:
        if n < 5:
            w -= 0.15
        elif n >= 100:
            w += 0.15
        elif n >= 30:
            w += 0.1
    if v.result == "unclear":
        w -= 0.1
    return round(max(0.2, min(0.8, w)), 2)


def to_evidence(v: ValidationInput) -> Evidence:
    sample = f" {v.sample_size}명" if v.sample_size else ""
    parts = [
        f"가설: {v.hypothesis}",
        f"결과: {RESULT_TEXT[v.result]}",
        v.target and f"대상: {v.target}",
        v.metric and f"핵심 수치: {v.metric}",
        v.note and f"메모: {v.note[:500]}",
        "창업가가 직접 수행해 제출한 검증(자가 보고)",
    ]
    return Evidence(
        title=f"창업가 검증 · {v.hypothesis[:60]}",
        source=f"창업가 검증 · {v.method or '방법 미기재'}{sample}",
        content=" / ".join(p for p in parts if p),
        confidence=strength(v),
    )


def _agent_of(query: str) -> str:
    # 고객·경쟁·수익 구조는 "에이전트명 + 아이디어"로 검색하고, 시장은 에이전트명 없이 여러 검색어를 쓴다
    head = query.split(" ", 1)[0]
    return head if head in SEARCHING_AGENTS else "MarketAgent"


def _route(v: ValidationInput) -> str:
    return AREA_ROUTE.get(v.area, v.area)


class UserValidationRetriever:
    """EvidenceRetriever 규약: 검색어를 보고 그 분야 검증 기록만 근거로 돌려준다"""

    def __init__(self, validations: list[ValidationInput]):
        self._validations = validations

    async def __call__(self, query: str) -> list[Evidence]:
        agent = _agent_of(query)
        return [to_evidence(v) for v in self._validations if _route(v) == agent]


class UserValidationRiskProvider:
    """RiskEvidenceProvider를 감싸 리스크 검증 기록을 '실행' 영역 근거로 더한다 (영역마다 중복되지 않게 한 곳에만)"""

    def __init__(self, inner, validations: list[ValidationInput]):
        self._inner = inner
        self._evidence = [to_evidence(v) for v in validations if v.area == "RiskAgent"]

    async def get_evidence(self, idea: BusinessIdea, category: RiskCategory) -> list[Evidence]:
        base = list(await self._inner.get_evidence(idea, category)) if self._inner else []
        return base + (self._evidence if category == RiskCategory.EXECUTION else [])

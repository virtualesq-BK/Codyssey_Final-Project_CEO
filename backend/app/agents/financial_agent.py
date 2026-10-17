"""
Financial Agent
LLM 은 변수 추출과 결과 해석만 담당하고, 모든 수치는 Python calculator 가 계산한다

BusinessIdea → (LLM) 변수 추출 → (RAG) benchmark 보완 → (Python) 계산 → (LLM) 해석 → AgentResult
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.base_agent import BaseAgent
from app.core.llm_provider import LLMProvider
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea, Evidence
from app.financial.benchmark import BenchmarkProvider, NullBenchmarkProvider
from app.financial.calculator import (
    INPUT_FIELDS,
    FinancialInputs,
    ScenarioName,
    ScenarioResult,
    run_scenarios,
)

logger = logging.getLogger(__name__)

# 사용자가 직접 제시한 수치는 검증되지 않은 추정치로 본다
USER_INPUT_CONFIDENCE: float = 0.6

# 상태·신뢰도 판단 기준이 되는 핵심 지표
CORE_METRICS: tuple[str, ...] = (
    "revenue",
    "gross_profit",
    "gross_margin",
    "cac",
    "ltv",
    "ltv_cac_ratio",
    "breakeven_units",
)

VARIABLE_LABELS: dict[str, str] = {
    "price": "고객 1인당 월 결제액",
    "customers": "월 결제 고객 수",
    "variable_cost_per_unit": "고객 1인당 월 변동비",
    "fixed_cost": "월 고정비",
    "acquisition_cost": "월 고객 획득 비용",
    "new_customers": "월 신규 고객 수",
    "monthly_churn_rate": "월 이탈률",
}

FORMULAS: dict[str, str] = {
    "revenue": "Price × Customers",
    "gross_profit": "Revenue - Variable Cost",
    "gross_margin": "Gross Profit / Revenue",
    "operating_profit": "Gross Profit - Fixed Cost",
    "cac": "Acquisition Cost / New Customers",
    "ltv": "Price × Gross Margin / Monthly Churn Rate",
    "ltv_cac_ratio": "LTV / CAC",
    "breakeven_units": "ceil(Fixed Cost / (Price - Variable Cost per Unit))",
}

_EXTRACTION_SYSTEM = """당신은 사업 아이디어 설명에서 재무 변수를 추출하는 분석가입니다.

규칙:
1. 설명에 명시적으로 적힌 수치만 추출하라.
2. 적혀 있지 않은 변수는 반드시 null 로 두라. 추정하거나 산업 평균으로 채우지 마라.
3. 어떤 계산도 하지 마라.
4. 금액은 원 단위 숫자, 기간은 월 기준, 이탈률은 0~1 사이 소수로 표기하라.
"""

_INTERPRETATION_SYSTEM = """당신은 창업 재무 분석 결과를 예비창업자에게 설명하는 컨설턴트입니다.

규칙:
1. 제공된 계산 결과의 수치만 인용하라. 새로운 수치를 만들거나 다시 계산하지 마라.
2. 계산되지 않은 지표는 "근거 부족 / 추가 검토 필요"로 표기하라.
3. 사업 성공을 보장하는 표현을 사용하지 마라.
"""


class FinancialInterpretation(BaseModel):
    summary: str = Field(..., min_length=1)
    recommendations: list[str] = Field(default_factory=list)


class FinancialAgent(BaseAgent):
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        agent_name: Optional[str] = None,
        benchmark_provider: Optional[BenchmarkProvider] = None,
        financial_inputs: Optional[FinancialInputs] = None,
    ):
        super().__init__(llm_provider=llm_provider, agent_name=agent_name)
        self._benchmarks: BenchmarkProvider = benchmark_provider or NullBenchmarkProvider()
        # 폼 등으로 이미 확보한 수치. LLM 추출값보다 우선한다.
        self._explicit_inputs = financial_inputs

    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        values: dict[str, float] = {}
        sources: dict[str, str] = {}
        evidence: list[Evidence] = []
        source_confidences: list[float] = []

        # 1. 변수 수집: 명시 입력 → LLM 추출 → benchmark 순으로 채운다
        self._merge(values, sources, self._explicit_inputs, "explicit_input")
        if len(values) < len(INPUT_FIELDS):
            self._merge(values, sources, await self._extract_variables(idea), "idea_text")

        if values:
            source_confidences.extend([USER_INPUT_CONFIDENCE] * len(values))
            evidence.append(
                Evidence(
                    title="사용자 제시 재무 변수",
                    source="BusinessIdea",
                    content=json.dumps(
                        {VARIABLE_LABELS[k]: v for k, v in values.items()}, ensure_ascii=False
                    ),
                    confidence=USER_INPUT_CONFIDENCE,
                )
            )

        # 2. 부족한 변수는 benchmark(RAG) 요청
        missing = [f for f in INPUT_FIELDS if f not in values]
        if missing:
            for benchmark in await self._request_benchmarks(idea, missing):
                values[benchmark.variable] = benchmark.value
                sources[benchmark.variable] = "benchmark"
                source_confidences.append(benchmark.evidence.confidence)
                evidence.append(benchmark.evidence)
        missing = [f for f in INPUT_FIELDS if f not in values]

        # 3. Python calculator 호출
        input_confidence = (
            sum(source_confidences) / len(source_confidences) if source_confidences else 0.0
        )
        scenarios = run_scenarios(FinancialInputs(**values), base_confidence=input_confidence)
        base = next(s for s in scenarios if s.scenario == ScenarioName.BASE)
        computed_core = [m for m in CORE_METRICS if base.metrics.get(m) is not None]
        coverage = len(computed_core) / len(CORE_METRICS)

        if computed_core:
            evidence.append(
                Evidence(
                    title="재무 지표 계산식",
                    source="Python deterministic calculator",
                    content=json.dumps(
                        {m: FORMULAS[m] for m in computed_core}, ensure_ascii=False
                    ),
                    confidence=1.0,
                )
            )

        # 4. 결과 해석
        interpretation = await self._interpret(idea, base, scenarios, missing)

        findings: list[dict[str, Any]] = [
            {"calculation_method": "deterministic_python"},
            {
                "inputs": {
                    k: {"label": VARIABLE_LABELS[k], "value": v, "source": sources[k]}
                    for k, v in values.items()
                }
            },
            {"missing_variables": [{"name": m, "label": VARIABLE_LABELS[m]} for m in missing]},
            {"base_metrics": base.metrics},
            {"scenarios": [s.model_dump(mode="json") for s in scenarios]},
            {"warnings": base.warnings},
        ]

        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS if coverage == 1.0 else AgentStatus.PARTIAL,
            summary=interpretation.summary,
            findings=findings,
            evidence=evidence,
            recommendations=interpretation.recommendations,
            confidence=round(coverage * input_confidence, 2),
        )

    @staticmethod
    def _merge(
        values: dict[str, float],
        sources: dict[str, str],
        inputs: Optional[FinancialInputs],
        source: str,
    ) -> None:
        if inputs is None:
            return
        for field, value in inputs.model_dump().items():
            if value is not None and field not in values:
                values[field] = value
                sources[field] = source

    async def _extract_variables(self, idea: BusinessIdea) -> Optional[FinancialInputs]:
        prompt = f"""다음 사업 아이디어 설명에서 재무 변수를 추출하라.

- 제목: {idea.title}
- 문제: {idea.problem}
- 고객: {idea.customer}
- 솔루션: {idea.solution}
- 산업: {idea.industry}
- 지역: {idea.location}

추출 대상 (명시되지 않았으면 null):
{json.dumps(VARIABLE_LABELS, ensure_ascii=False, indent=2)}

위 key 를 그대로 사용한 JSON 으로만 응답하라."""
        try:
            return await self.llm.generate_structured(prompt, FinancialInputs, system=_EXTRACTION_SYSTEM)
        except Exception as exc:
            logger.warning("[%s] 재무 변수 추출 실패, 변수 없음으로 진행: %s", self.agent_name, exc)
            return None

    async def _request_benchmarks(self, idea: BusinessIdea, missing: list[str]) -> list:
        try:
            benchmarks = await self._benchmarks.get_benchmarks(idea, missing)
        except Exception as exc:
            logger.warning("[%s] benchmark 조회 실패: %s", self.agent_name, exc)
            return []
        # 요청하지 않은 변수나 중복은 무시한다
        seen: set[str] = set()
        accepted = []
        for benchmark in benchmarks:
            if benchmark.variable in missing and benchmark.variable not in seen:
                seen.add(benchmark.variable)
                accepted.append(benchmark)
        return accepted

    async def _interpret(
        self,
        idea: BusinessIdea,
        base: ScenarioResult,
        scenarios: list[ScenarioResult],
        missing: list[str],
    ) -> FinancialInterpretation:
        fallback = self._fallback_interpretation(base, missing)
        if not any(v is not None for v in base.metrics.values()):
            return fallback  # 해석할 수치가 없으면 LLM 을 호출하지 않는다

        prompt = f"""'{idea.title}' 사업의 재무 계산 결과를 해석하라.

## 계산 결과 (Python 계산값, 수정 금지)
{json.dumps({s.scenario.value: s.metrics for s in scenarios}, ensure_ascii=False, indent=2)}

## 계산하지 못한 원인
- 부족한 변수: {[VARIABLE_LABELS[m] for m in missing] or '없음'}
- 경고: {base.warnings or '없음'}

반드시 아래 JSON 형식으로만 응답하라:
{{
  "summary": "재무 해석 요약 (2-3문장)",
  "recommendations": ["권고1", "권고2"]
}}"""
        try:
            return await self.llm.generate_structured(
                prompt, FinancialInterpretation, system=_INTERPRETATION_SYSTEM
            )
        except Exception as exc:
            logger.warning("[%s] 해석 생성 실패, 기본 해석 사용: %s", self.agent_name, exc)
            return fallback

    @staticmethod
    def _fallback_interpretation(base: ScenarioResult, missing: list[str]) -> FinancialInterpretation:
        """LLM 없이 계산 결과만으로 만드는 해석"""
        m = base.metrics
        parts: list[str] = []
        if m.get("revenue") is not None:
            parts.append(f"월 매출 {m['revenue']:,.0f}원")
        if m.get("gross_margin") is not None:
            parts.append(f"매출총이익률 {m['gross_margin']:.1%}")
        if m.get("ltv_cac_ratio") is not None:
            parts.append(f"LTV/CAC {m['ltv_cac_ratio']:.2f}배")
        if m.get("breakeven_units") is not None:
            parts.append(f"손익분기 고객 수 {m['breakeven_units']:,}명")

        if parts:
            summary = "Base 시나리오 기준 " + ", ".join(parts) + "."
        else:
            summary = "재무 변수가 부족하여 계산하지 못했습니다. 근거 부족 / 추가 검토 필요."
        if missing:
            summary += f" 부족한 변수 {len(missing)}개로 일부 지표는 계산하지 않았습니다."

        recommendations = [f"{VARIABLE_LABELS[v]} 추정치 확보 필요" for v in missing]
        recommendations.extend(base.warnings)
        return FinancialInterpretation(summary=summary, recommendations=recommendations)

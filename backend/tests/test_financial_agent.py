"""
Financial Agent tests – LLM 문장이 아닌 계산값과 schema 를 검증한다
"""
import json

import pytest

from app.agents.financial_agent import FinancialAgent
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentStatus, BusinessIdea, Evidence
from app.financial.benchmark import Benchmark
from app.financial.calculator import FinancialInputs

FULL_VARIABLES = {
    "price": 10_000,
    "customers": 500,
    "variable_cost_per_unit": 4_000,
    "fixed_cost": 2_000_000,
    "acquisition_cost": 1_000_000,
    "new_customers": 100,
    "monthly_churn_rate": 0.05,
}
INTERPRETATION = json.dumps({"summary": "LLM 해석", "recommendations": ["권고 A"]}, ensure_ascii=False)


def make_idea() -> BusinessIdea:
    return BusinessIdea(
        idea_id="fin-001",
        title="배달 세탁 구독",
        problem="바쁜 직장인이 세탁소 방문 시간 없음",
        customer="25-40대 직장인",
        solution="월 10,000원 구독형 픽업 세탁",
        industry="생활서비스",
    )


def make_agent(responses: list[str], **kwargs) -> FinancialAgent:
    llm = MockProvider()
    llm.set_responses(responses)
    return FinancialAgent(llm_provider=llm, **kwargs)


def finding(result, key):
    return next(f[key] for f in result.findings if key in f)


class StubBenchmarkProvider:
    def __init__(self, benchmarks):
        self.benchmarks = benchmarks
        self.requested: list[str] = []

    async def get_benchmarks(self, idea, variables):
        self.requested = list(variables)
        return self.benchmarks


def benchmark(variable: str, value: float, confidence: float = 0.8) -> Benchmark:
    return Benchmark(
        variable=variable,
        value=value,
        evidence=Evidence(title=f"{variable} 산업 평균", source="RAG", content=str(value), confidence=confidence),
    )


async def test_full_variables_produce_calculated_metrics():
    agent = make_agent([json.dumps(FULL_VARIABLES), INTERPRETATION])
    result = await agent.run(make_idea())

    assert result.agent_name == "FinancialAgent"
    assert result.status == AgentStatus.SUCCESS
    metrics = finding(result, "base_metrics")
    assert metrics["revenue"] == 5_000_000
    assert metrics["gross_profit"] == 3_000_000
    assert metrics["gross_margin"] == 0.6
    assert metrics["cac"] == 10_000
    assert metrics["ltv"] == 120_000
    assert metrics["ltv_cac_ratio"] == 12.0
    assert metrics["breakeven_units"] == 334
    assert finding(result, "missing_variables") == []
    assert finding(result, "calculation_method") == "deterministic_python"
    assert result.summary == "LLM 해석"
    assert result.recommendations == ["권고 A"]
    assert result.confidence == 0.6


async def test_three_scenarios_in_findings():
    agent = make_agent([json.dumps(FULL_VARIABLES), INTERPRETATION])
    result = await agent.run(make_idea())
    scenarios = finding(result, "scenarios")
    assert [s["scenario"] for s in scenarios] == ["conservative", "base", "optimistic"]
    for s in scenarios:
        assert {"scenario", "assumptions", "metrics", "confidence"} <= s.keys()


async def test_llm_supplied_numbers_do_not_override_calculation():
    """LLM 이 계산 결과를 같이 보내도 무시하고 Python 계산값을 사용한다"""
    extraction = {**FULL_VARIABLES, "revenue": 999, "ltv": 1, "breakeven_units": 1}
    agent = make_agent([json.dumps(extraction), INTERPRETATION])
    result = await agent.run(make_idea())
    metrics = finding(result, "base_metrics")
    assert metrics["revenue"] == 5_000_000
    assert metrics["ltv"] == 120_000
    assert metrics["breakeven_units"] == 334


async def test_missing_variables_are_identified_not_invented():
    agent = make_agent([json.dumps({"price": 10_000, "customers": 500}), INTERPRETATION])
    result = await agent.run(make_idea())

    assert result.status == AgentStatus.PARTIAL
    metrics = finding(result, "base_metrics")
    assert metrics["revenue"] == 5_000_000
    assert metrics["cac"] is None
    assert metrics["ltv"] is None
    assert metrics["breakeven_units"] is None
    missing = [m["name"] for m in finding(result, "missing_variables")]
    assert missing == [
        "variable_cost_per_unit",
        "fixed_cost",
        "acquisition_cost",
        "new_customers",
        "monthly_churn_rate",
    ]
    assert 0 < result.confidence < 0.6


async def test_no_variables_returns_partial_without_numbers():
    agent = make_agent(['{"result": "mock response"}'])
    result = await agent.run(make_idea())

    assert result.status == AgentStatus.PARTIAL
    assert all(v is None for v in finding(result, "base_metrics").values())
    assert len(finding(result, "missing_variables")) == 7
    assert result.confidence == 0.0
    assert result.evidence == []
    assert len(result.recommendations) == 7
    # 변수 추출 1회만 호출 – 해석할 수치가 없으면 LLM 을 다시 부르지 않는다
    assert len(agent.get_token_usages()) == 1


async def test_unparseable_extraction_is_handled_without_retry():
    agent = make_agent(["JSON 이 아닌 응답"])
    result = await agent.run(make_idea())
    assert result.status == AgentStatus.PARTIAL
    assert result.error_message is None


async def test_interpretation_failure_falls_back_to_calculated_summary():
    agent = make_agent([json.dumps(FULL_VARIABLES), "JSON 이 아닌 응답"])
    result = await agent.run(make_idea())
    assert result.status == AgentStatus.SUCCESS
    assert "5,000,000" in result.summary
    assert finding(result, "base_metrics")["revenue"] == 5_000_000


async def test_explicit_inputs_skip_extraction_and_take_priority():
    agent = make_agent([INTERPRETATION], financial_inputs=FinancialInputs(**FULL_VARIABLES))
    result = await agent.run(make_idea())
    assert result.status == AgentStatus.SUCCESS
    assert len(agent.get_token_usages()) == 1  # 해석 1회만
    inputs = finding(result, "inputs")
    assert all(v["source"] == "explicit_input" for v in inputs.values())


async def test_explicit_inputs_override_extracted_values():
    agent = make_agent(
        [json.dumps(FULL_VARIABLES), INTERPRETATION],
        financial_inputs=FinancialInputs(price=20_000),
    )
    result = await agent.run(make_idea())
    inputs = finding(result, "inputs")
    assert inputs["price"] == {"label": "고객 1인당 월 결제액", "value": 20_000, "source": "explicit_input"}
    assert inputs["customers"]["source"] == "idea_text"
    assert finding(result, "base_metrics")["revenue"] == 10_000_000


async def test_benchmark_fills_missing_variables_and_python_calculates():
    provider = StubBenchmarkProvider(
        [benchmark("monthly_churn_rate", 0.05), benchmark("price", 1)]  # price 는 요청 대상이 아님
    )
    variables = {k: v for k, v in FULL_VARIABLES.items() if k != "monthly_churn_rate"}
    agent = make_agent([json.dumps(variables), INTERPRETATION], benchmark_provider=provider)
    result = await agent.run(make_idea())

    assert provider.requested == ["monthly_churn_rate"]
    assert result.status == AgentStatus.SUCCESS
    inputs = finding(result, "inputs")
    assert inputs["monthly_churn_rate"]["source"] == "benchmark"
    assert inputs["price"]["value"] == 10_000
    assert finding(result, "base_metrics")["ltv"] == 120_000
    assert "RAG" in [e.source for e in result.evidence]


async def test_benchmark_provider_failure_is_tolerated():
    class Broken:
        async def get_benchmarks(self, idea, variables):
            raise RuntimeError("RAG down")

    agent = make_agent([json.dumps({"price": 10_000, "customers": 500}), INTERPRETATION], benchmark_provider=Broken())
    result = await agent.run(make_idea())
    assert result.status == AgentStatus.PARTIAL
    assert finding(result, "base_metrics")["revenue"] == 5_000_000


async def test_invalid_extracted_value_is_reported_not_calculated():
    variables = {**FULL_VARIABLES, "new_customers": 0}
    agent = make_agent([json.dumps(variables), INTERPRETATION])
    result = await agent.run(make_idea())

    assert result.status == AgentStatus.PARTIAL
    assert finding(result, "base_metrics")["cac"] is None
    base = next(s for s in finding(result, "scenarios") if s["scenario"] == "base")
    assert any(i["metric"] == "cac" and i["kind"] == "undefined" for i in base["issues"])


async def test_evidence_links_inputs_and_formulas():
    agent = make_agent([json.dumps(FULL_VARIABLES), INTERPRETATION])
    result = await agent.run(make_idea())
    sources = [e.source for e in result.evidence]
    assert sources == ["BusinessIdea", "Python deterministic calculator"]
    json.dumps(result.findings, ensure_ascii=False)  # DecisionAgent 가 직렬화할 수 있어야 한다

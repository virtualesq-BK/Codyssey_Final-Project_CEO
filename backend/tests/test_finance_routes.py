from app.api.finance_routes import ScenarioRequest, scenarios
from app.financial.calculator import FinancialInputs


async def test_scenarios_compute_three_cases():
    res = await scenarios(ScenarioRequest(inputs=FinancialInputs(
        price=150000, customers=40, variable_cost_per_unit=20000, fixed_cost=3000000,
        acquisition_cost=1000000, new_customers=8, monthly_churn_rate=0.05)))
    names = [s.scenario.value for s in res.scenarios]
    assert names == ["conservative", "base", "optimistic"]
    base = res.scenarios[1].metrics
    assert base["revenue"] == 6000000
    assert base["breakeven_units"] == 24


async def test_scenarios_report_missing_inputs():
    res = await scenarios(ScenarioRequest(inputs=FinancialInputs(price=10000)))
    assert res.scenarios[1].metrics["revenue"] is None
    assert res.scenarios[1].issues


async def test_estimate_keeps_only_requested_fields(monkeypatch):
    import json

    from app.api import finance_routes
    from app.api.finance_routes import EstimateField, EstimateRequest, estimate
    from app.core.llm_provider import MockProvider

    llm = MockProvider()
    llm.set_responses([json.dumps({"values": [
        {"key": "price", "value": 15000, "basis": "경쟁 서비스 참고"},
        {"key": "customers", "value": -3, "basis": "음수는 버림"},
        {"key": "hacked", "value": 1, "basis": "요청 안 한 칸"},
    ]}, ensure_ascii=False)])
    monkeypatch.setattr(finance_routes, "_llm", lambda: llm)
    res = await estimate(EstimateRequest(
        revenue_type="구독형",
        fields=[EstimateField(key="price", label="월 구독료", unit="원"), EstimateField(key="customers", label="구독자 수", unit="명")],
    ))
    assert [(v.key, v.value) for v in res.values] == [("price", 15000)]

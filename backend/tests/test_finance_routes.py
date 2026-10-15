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

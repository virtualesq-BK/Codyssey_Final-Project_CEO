"""
Financial calculator unit tests – 계산값과 validation 검증 (LLM 호출 없음)
"""
import math

import pytest

from app.financial.calculator import (
    FinancialInputs,
    InvalidInputError,
    MissingInputError,
    ScenarioName,
    UndefinedResultError,
    calculate_breakeven,
    calculate_cac,
    calculate_gross_margin,
    calculate_gross_profit,
    calculate_ltv,
    calculate_ltv_cac_ratio,
    calculate_operating_profit,
    calculate_revenue,
    calculate_unit_contribution,
    calculate_variable_cost,
    compute_metrics,
    run_scenario,
    run_scenarios,
)


def full_inputs(**overrides) -> FinancialInputs:
    data = dict(
        price=10_000,
        customers=500,
        variable_cost_per_unit=4_000,
        fixed_cost=2_000_000,
        acquisition_cost=1_000_000,
        new_customers=100,
        monthly_churn_rate=0.05,
    )
    data.update(overrides)
    return FinancialInputs(**data)


# ── Revenue ──────────────────────────────────────────

def test_revenue():
    assert calculate_revenue(10_000, 500) == 5_000_000


def test_revenue_zero_customers_is_zero():
    assert calculate_revenue(10_000, 0) == 0


def test_revenue_zero_price_is_zero():
    assert calculate_revenue(0, 500) == 0


@pytest.mark.parametrize("price, customers", [(-1, 10), (10, -1)])
def test_revenue_negative_input_rejected(price, customers):
    with pytest.raises(InvalidInputError):
        calculate_revenue(price, customers)


@pytest.mark.parametrize("price, customers", [(None, 10), (10, None)])
def test_revenue_missing_input(price, customers):
    with pytest.raises(MissingInputError):
        calculate_revenue(price, customers)


@pytest.mark.parametrize("bad", ["1000", True, math.nan, math.inf, 1e17])
def test_revenue_invalid_or_unrealistic_input(bad):
    with pytest.raises(InvalidInputError):
        calculate_revenue(bad, 10)


# ── Gross Profit / Margin ────────────────────────────

def test_variable_cost():
    assert calculate_variable_cost(4_000, 500) == 2_000_000


def test_gross_profit():
    assert calculate_gross_profit(5_000_000, 2_000_000) == 3_000_000


def test_gross_profit_can_be_negative():
    assert calculate_gross_profit(1_000, 1_500) == -500


def test_gross_profit_negative_cost_rejected():
    with pytest.raises(InvalidInputError) as exc:
        calculate_gross_profit(1_000, -1)
    assert exc.value.field == "variable_cost"


def test_gross_margin():
    assert calculate_gross_margin(3_000_000, 5_000_000) == pytest.approx(0.6)


def test_gross_margin_negative_profit():
    assert calculate_gross_margin(-500, 1_000) == pytest.approx(-0.5)


def test_gross_margin_zero_revenue_is_undefined():
    with pytest.raises(UndefinedResultError):
        calculate_gross_margin(0, 0)


def test_gross_margin_profit_above_revenue_rejected():
    with pytest.raises(InvalidInputError):
        calculate_gross_margin(2_000, 1_000)


def test_operating_profit():
    assert calculate_operating_profit(3_000_000, 2_000_000) == 1_000_000
    assert calculate_operating_profit(1_000_000, 2_000_000) == -1_000_000


# ── CAC ──────────────────────────────────────────────

def test_cac():
    assert calculate_cac(1_000_000, 100) == 10_000


def test_cac_zero_new_customers_is_undefined():
    with pytest.raises(UndefinedResultError):
        calculate_cac(1_000_000, 0)


def test_cac_missing_input():
    with pytest.raises(MissingInputError):
        calculate_cac(None, 100)


def test_cac_negative_cost_rejected():
    with pytest.raises(InvalidInputError):
        calculate_cac(-1, 100)


# ── LTV / LTV:CAC ────────────────────────────────────

def test_ltv():
    assert calculate_ltv(10_000, 0.6, 0.05) == pytest.approx(120_000)


def test_ltv_zero_churn_is_undefined():
    with pytest.raises(UndefinedResultError):
        calculate_ltv(10_000, 0.6, 0)


@pytest.mark.parametrize("churn", [-0.1, 1.5])
def test_ltv_churn_out_of_range_rejected(churn):
    with pytest.raises(InvalidInputError):
        calculate_ltv(10_000, 0.6, churn)


def test_ltv_margin_above_one_rejected():
    with pytest.raises(InvalidInputError):
        calculate_ltv(10_000, 1.2, 0.05)


def test_ltv_missing_churn():
    with pytest.raises(MissingInputError):
        calculate_ltv(10_000, 0.6, None)


def test_ltv_cac_ratio():
    assert calculate_ltv_cac_ratio(120_000, 10_000) == pytest.approx(12.0)


def test_ltv_cac_ratio_zero_cac_is_undefined():
    with pytest.raises(UndefinedResultError):
        calculate_ltv_cac_ratio(120_000, 0)


# ── Break-even ───────────────────────────────────────

def test_unit_contribution():
    assert calculate_unit_contribution(10_000, 4_000) == 6_000


def test_breakeven_rounds_up():
    result = calculate_breakeven(2_000_000, 10_000, 4_000)
    assert result.unit_contribution == 6_000
    assert result.breakeven_units == 334  # 333.33… → 올림
    assert result.breakeven_revenue == 3_340_000


def test_breakeven_zero_fixed_cost():
    assert calculate_breakeven(0, 10_000, 4_000).breakeven_units == 0


@pytest.mark.parametrize("price, unit_cost", [(4_000, 4_000), (3_000, 4_000), (0, 0)])
def test_breakeven_non_positive_contribution_is_undefined(price, unit_cost):
    with pytest.raises(UndefinedResultError):
        calculate_breakeven(2_000_000, price, unit_cost)


def test_breakeven_missing_fixed_cost():
    with pytest.raises(MissingInputError) as exc:
        calculate_breakeven(None, 10_000, 4_000)
    assert exc.value.field == "fixed_cost"


# ── compute_metrics ──────────────────────────────────

def test_compute_metrics_full_inputs():
    result = compute_metrics(full_inputs())
    m = result.metrics
    assert m.revenue == 5_000_000
    assert m.variable_cost == 2_000_000
    assert m.gross_profit == 3_000_000
    assert m.gross_margin == 0.6
    assert m.operating_profit == 1_000_000
    assert m.cac == 10_000
    assert m.ltv == 120_000
    assert m.ltv_cac_ratio == 12.0
    assert m.breakeven_units == 334
    assert result.issues == []
    assert result.missing_inputs == []


def test_compute_metrics_partial_inputs_computes_only_what_it_can():
    result = compute_metrics(FinancialInputs(price=10_000, customers=500))
    assert result.metrics.revenue == 5_000_000
    assert result.metrics.gross_profit is None
    assert result.metrics.cac is None
    assert result.metrics.breakeven_units is None
    assert result.computed == ["revenue"]
    assert result.missing_inputs == [
        "variable_cost_per_unit",
        "fixed_cost",
        "acquisition_cost",
        "new_customers",
        "monthly_churn_rate",
    ]


def test_compute_metrics_no_inputs_returns_no_numbers():
    result = compute_metrics(FinancialInputs())
    assert result.computed == []
    assert set(result.missing_inputs) == set(FinancialInputs.model_fields)


def test_compute_metrics_never_returns_nan():
    result = compute_metrics(full_inputs(customers=0, new_customers=0, monthly_churn_rate=0))
    for value in result.metrics.model_dump().values():
        assert value is None or not math.isnan(value)
    assert result.metrics.revenue == 0
    assert result.metrics.gross_margin is None
    assert result.metrics.cac is None
    undefined = {i.metric for i in result.issues if i.kind == "undefined"}
    assert {"gross_margin", "cac"} <= undefined


def test_compute_metrics_reports_invalid_input():
    result = compute_metrics(full_inputs(variable_cost_per_unit=-100))
    invalid = [i for i in result.issues if i.kind == "invalid_input"]
    assert invalid and invalid[0].field == "variable_cost_per_unit"
    assert result.metrics.gross_profit is None
    assert result.metrics.revenue == 5_000_000


def test_compute_metrics_zero_cac_warns_and_skips_ratio():
    result = compute_metrics(full_inputs(acquisition_cost=0))
    assert result.metrics.cac == 0
    assert result.metrics.ltv_cac_ratio is None
    assert any("CAC" in w for w in result.warnings)


def test_compute_metrics_warns_on_unrealistic_ltv_cac():
    result = compute_metrics(full_inputs(monthly_churn_rate=0.001))
    assert result.metrics.ltv_cac_ratio > 20
    assert any("LTV/CAC" in w for w in result.warnings)


def test_compute_metrics_warns_on_negative_margin():
    result = compute_metrics(full_inputs(variable_cost_per_unit=12_000))
    assert result.metrics.gross_margin == -0.2
    assert result.metrics.breakeven_units is None
    assert any("음수" in w for w in result.warnings)


# ── Scenario analysis ────────────────────────────────

def test_run_scenarios_returns_three_in_order():
    scenarios = run_scenarios(full_inputs())
    assert [s.scenario for s in scenarios] == [
        ScenarioName.CONSERVATIVE,
        ScenarioName.BASE,
        ScenarioName.OPTIMISTIC,
    ]


def test_scenario_output_structure():
    dumped = run_scenario(full_inputs(), ScenarioName.BASE, base_confidence=0.6).model_dump(mode="json")
    assert dumped["scenario"] == "base"
    assert {"scenario", "assumptions", "metrics", "confidence"} <= dumped.keys()
    assert dumped["assumptions"]["multipliers"] == {}
    assert dumped["assumptions"]["inputs"]["price"] == 10_000
    assert dumped["confidence"] == 0.6


def test_base_scenario_matches_compute_metrics():
    base = run_scenario(full_inputs(), ScenarioName.BASE)
    assert base.metrics == compute_metrics(full_inputs()).metrics.model_dump()


def test_conservative_scenario_values():
    s = run_scenario(full_inputs(), ScenarioName.CONSERVATIVE, base_confidence=0.5)
    assert s.assumptions["inputs"]["customers"] == pytest.approx(350)
    assert s.metrics["revenue"] == 3_500_000          # 10,000 × 350
    assert s.metrics["variable_cost"] == 1_540_000    # 4,400 × 350
    assert s.metrics["gross_margin"] == 0.56
    assert s.metrics["cac"] == pytest.approx(17_142.86)  # 1,200,000 / 70
    assert s.metrics["ltv"] == pytest.approx(93_333.33)  # 10,000 × 0.56 / 0.06
    assert s.metrics["breakeven_units"] == 358        # ceil(2,000,000 / 5,600)
    assert s.confidence == 0.4


def test_scenarios_are_ordered_by_outcome():
    conservative, base, optimistic = run_scenarios(full_inputs())
    for metric in ("revenue", "gross_profit", "ltv", "ltv_cac_ratio"):
        assert conservative.metrics[metric] < base.metrics[metric] < optimistic.metrics[metric]
    assert conservative.metrics["cac"] > base.metrics["cac"] > optimistic.metrics["cac"]
    assert conservative.confidence < base.confidence
    assert optimistic.confidence < base.confidence


def test_scenario_churn_capped_at_one():
    s = run_scenario(full_inputs(monthly_churn_rate=0.9), ScenarioName.CONSERVATIVE)
    assert s.assumptions["inputs"]["monthly_churn_rate"] == 1.0
    assert s.metrics["ltv"] is not None


def test_scenario_with_missing_inputs_keeps_them_missing():
    s = run_scenario(FinancialInputs(price=10_000, customers=100), ScenarioName.OPTIMISTIC)
    assert s.metrics["revenue"] == 1_300_000
    assert s.metrics["cac"] is None
    assert s.assumptions["inputs"]["acquisition_cost"] is None


def test_scenario_invalid_confidence_rejected():
    with pytest.raises(InvalidInputError):
        run_scenario(full_inputs(), ScenarioName.BASE, base_confidence=1.5)


def test_scenario_unknown_multiplier_rejected():
    with pytest.raises(InvalidInputError):
        run_scenario(full_inputs(), ScenarioName.BASE, multipliers={"unknown": 2.0})

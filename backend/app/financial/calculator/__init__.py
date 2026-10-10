"""
Deterministic Financial Calculation Service
LLM 이 아닌 Python 이 모든 재무 수치를 계산한다
"""
from app.financial.calculator.breakeven import (
    BreakEvenResult,
    calculate_breakeven,
    calculate_unit_contribution,
)
from app.financial.calculator.cac import calculate_cac
from app.financial.calculator.errors import (
    CalculationError,
    InvalidInputError,
    MissingInputError,
    UndefinedResultError,
)
from app.financial.calculator.ltv import calculate_ltv, calculate_ltv_cac_ratio
from app.financial.calculator.profit import (
    calculate_gross_margin,
    calculate_gross_profit,
    calculate_operating_profit,
    calculate_variable_cost,
)
from app.financial.calculator.revenue import calculate_revenue
from app.financial.calculator.scenarios import (
    INPUT_FIELDS,
    METRIC_FIELDS,
    FinancialInputs,
    FinancialMetrics,
    MetricIssue,
    MetricsResult,
    ScenarioName,
    ScenarioResult,
    compute_metrics,
    run_scenario,
    run_scenarios,
)

__all__ = [
    "BreakEvenResult",
    "CalculationError",
    "FinancialInputs",
    "FinancialMetrics",
    "INPUT_FIELDS",
    "InvalidInputError",
    "METRIC_FIELDS",
    "MetricIssue",
    "MetricsResult",
    "MissingInputError",
    "ScenarioName",
    "ScenarioResult",
    "UndefinedResultError",
    "calculate_breakeven",
    "calculate_cac",
    "calculate_gross_margin",
    "calculate_gross_profit",
    "calculate_ltv",
    "calculate_ltv_cac_ratio",
    "calculate_operating_profit",
    "calculate_revenue",
    "calculate_unit_contribution",
    "calculate_variable_cost",
    "compute_metrics",
    "run_scenario",
    "run_scenarios",
]

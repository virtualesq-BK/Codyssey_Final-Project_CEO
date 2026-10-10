"""
Scenario Analysis – Conservative / Base / Optimistic

입력 변수 묶음(FinancialInputs)으로 계산 가능한 지표를 모두 계산하고,
계산하지 못한 지표는 사유(issue)를 남긴다. 값을 추정해서 채우지 않는다.

단위 가정: 금액은 원, 기간은 월. customers 는 월 결제 고객 수이며
고객 1인이 월 1단위(price)를 결제한다고 본다.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from app.financial.calculator.breakeven import calculate_breakeven
from app.financial.calculator.cac import calculate_cac
from app.financial.calculator.errors import (
    CalculationError,
    InvalidInputError,
    MissingInputError,
)
from app.financial.calculator.ltv import LTV_ASSUMPTION, calculate_ltv, calculate_ltv_cac_ratio
from app.financial.calculator.profit import (
    calculate_gross_margin,
    calculate_gross_profit,
    calculate_operating_profit,
    calculate_variable_cost,
)
from app.financial.calculator.revenue import calculate_revenue
from app.financial.calculator.validation import require_rate

# LTV/CAC 가 이 값을 넘으면 가정이 비현실적일 가능성이 높다고 경고한다
UNREALISTIC_LTV_CAC_RATIO: float = 20.0


class ScenarioName(str, Enum):
    CONSERVATIVE = "conservative"
    BASE = "base"
    OPTIMISTIC = "optimistic"


# 시나리오별 입력 변수 배수. 산업별 근거가 아닌 일반적인 민감도 가정이다.
SCENARIO_MULTIPLIERS: dict[ScenarioName, dict[str, float]] = {
    ScenarioName.CONSERVATIVE: {
        "customers": 0.7,
        "new_customers": 0.7,
        "variable_cost_per_unit": 1.1,
        "acquisition_cost": 1.2,
        "monthly_churn_rate": 1.2,
    },
    ScenarioName.BASE: {},
    ScenarioName.OPTIMISTIC: {
        "customers": 1.3,
        "new_customers": 1.3,
        "variable_cost_per_unit": 0.95,
        "acquisition_cost": 0.9,
        "monthly_churn_rate": 0.8,
    },
}

# Base 대비 일반 배수로 파생된 시나리오의 신뢰도 할인
DERIVED_SCENARIO_CONFIDENCE_FACTOR: float = 0.8


class FinancialInputs(BaseModel):
    price: Optional[float] = Field(default=None, description="고객 1인당 월 결제액 (원)")
    customers: Optional[float] = Field(default=None, description="월 결제 고객 수")
    variable_cost_per_unit: Optional[float] = Field(default=None, description="고객 1인당 월 변동비 (원)")
    fixed_cost: Optional[float] = Field(default=None, description="월 고정비 (원)")
    acquisition_cost: Optional[float] = Field(default=None, description="월 고객 획득 비용 총액 (원)")
    new_customers: Optional[float] = Field(default=None, description="월 신규 고객 수")
    monthly_churn_rate: Optional[float] = Field(default=None, description="월 이탈률 (0~1)")


INPUT_FIELDS: tuple[str, ...] = tuple(FinancialInputs.model_fields.keys())


class FinancialMetrics(BaseModel):
    revenue: Optional[float] = None
    variable_cost: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_profit: Optional[float] = None
    cac: Optional[float] = None
    ltv: Optional[float] = None
    ltv_cac_ratio: Optional[float] = None
    unit_contribution: Optional[float] = None
    breakeven_units: Optional[int] = None
    breakeven_revenue: Optional[float] = None


METRIC_FIELDS: tuple[str, ...] = tuple(FinancialMetrics.model_fields.keys())


class MetricIssue(BaseModel):
    metric: str
    kind: str  # missing_input | invalid_input | undefined
    field: str
    message: str


class MetricsResult(BaseModel):
    metrics: FinancialMetrics
    issues: list[MetricIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)  # 값이 없는 입력 변수

    @property
    def computed(self) -> list[str]:
        return [m for m in METRIC_FIELDS if getattr(self.metrics, m) is not None]


class ScenarioResult(BaseModel):
    scenario: ScenarioName
    assumptions: dict[str, Any]
    metrics: dict[str, Any]
    issues: list[MetricIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


def _issue_kind(exc: CalculationError) -> str:
    if isinstance(exc, MissingInputError):
        return "missing_input"
    if isinstance(exc, InvalidInputError):
        return "invalid_input"
    return "undefined"


def compute_metrics(inputs: FinancialInputs) -> MetricsResult:
    """계산 가능한 지표만 계산한다. 실패한 지표는 None 으로 두고 issue 를 기록한다."""
    issues: list[MetricIssue] = []

    def attempt(metric: str, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except CalculationError as exc:
            issues.append(
                MetricIssue(metric=metric, kind=_issue_kind(exc), field=exc.field, message=exc.message)
            )
            return None

    i = inputs
    revenue = attempt("revenue", lambda: calculate_revenue(i.price, i.customers))
    variable_cost = attempt(
        "variable_cost", lambda: calculate_variable_cost(i.variable_cost_per_unit, i.customers)
    )
    gross_profit = attempt("gross_profit", lambda: calculate_gross_profit(revenue, variable_cost))
    gross_margin = attempt("gross_margin", lambda: calculate_gross_margin(gross_profit, revenue))
    operating_profit = attempt(
        "operating_profit", lambda: calculate_operating_profit(gross_profit, i.fixed_cost)
    )
    cac = attempt("cac", lambda: calculate_cac(i.acquisition_cost, i.new_customers))
    ltv = attempt("ltv", lambda: calculate_ltv(i.price, gross_margin, i.monthly_churn_rate))
    ltv_cac_ratio = attempt("ltv_cac_ratio", lambda: calculate_ltv_cac_ratio(ltv, cac))
    breakeven = attempt(
        "breakeven", lambda: calculate_breakeven(i.fixed_cost, i.price, i.variable_cost_per_unit)
    )

    warnings: list[str] = []
    if gross_margin is not None and gross_margin < 0:
        warnings.append("변동비가 매출보다 커서 매출총이익률이 음수입니다")
    if cac == 0:
        warnings.append("CAC가 0입니다. 고객 획득 비용이 누락되지 않았는지 확인이 필요합니다")
    if ltv_cac_ratio is not None and ltv_cac_ratio > UNREALISTIC_LTV_CAC_RATIO:
        warnings.append(
            f"LTV/CAC가 {UNREALISTIC_LTV_CAC_RATIO:g}배를 초과합니다. 이탈률·CAC 가정이 비현실적일 수 있습니다"
        )

    def money(v: Optional[float]) -> Optional[float]:
        return None if v is None else round(v, 2)

    def ratio(v: Optional[float]) -> Optional[float]:
        return None if v is None else round(v, 4)

    metrics = FinancialMetrics(
        revenue=money(revenue),
        variable_cost=money(variable_cost),
        gross_profit=money(gross_profit),
        gross_margin=ratio(gross_margin),
        operating_profit=money(operating_profit),
        cac=money(cac),
        ltv=money(ltv),
        ltv_cac_ratio=ratio(ltv_cac_ratio),
        unit_contribution=money(breakeven.unit_contribution) if breakeven else None,
        breakeven_units=breakeven.breakeven_units if breakeven else None,
        breakeven_revenue=money(breakeven.breakeven_revenue) if breakeven else None,
    )
    missing_inputs = [f for f in INPUT_FIELDS if getattr(inputs, f) is None]
    return MetricsResult(
        metrics=metrics, issues=issues, warnings=warnings, missing_inputs=missing_inputs
    )


def apply_multipliers(inputs: FinancialInputs, multipliers: dict[str, float]) -> FinancialInputs:
    """입력 변수에 시나리오 배수를 적용한다. 없는 값은 그대로 None 이다."""
    data = inputs.model_dump()
    for field, factor in multipliers.items():
        if field not in data:
            raise InvalidInputError(field, "알 수 없는 입력 변수입니다")
        if data[field] is not None:
            data[field] = data[field] * factor
    churn = data.get("monthly_churn_rate")
    if churn is not None and churn > 1.0 and (inputs.monthly_churn_rate or 0) <= 1.0:
        data["monthly_churn_rate"] = 1.0  # 배수 적용으로 100%를 넘지 않게 한다
    return FinancialInputs(**data)


def run_scenario(
    inputs: FinancialInputs,
    scenario: ScenarioName,
    base_confidence: float = 0.5,
    multipliers: Optional[dict[str, float]] = None,
) -> ScenarioResult:
    factors = SCENARIO_MULTIPLIERS[scenario] if multipliers is None else multipliers
    adjusted = apply_multipliers(inputs, factors)
    result = compute_metrics(adjusted)

    confidence = require_rate("base_confidence", base_confidence)
    if scenario != ScenarioName.BASE:
        confidence *= DERIVED_SCENARIO_CONFIDENCE_FACTOR

    return ScenarioResult(
        scenario=scenario,
        assumptions={
            "multipliers": dict(factors),
            "inputs": adjusted.model_dump(),
            "notes": [
                "금액 단위는 원, 기간 단위는 월",
                "고객 1인이 월 1회 price 를 결제한다고 가정",
                LTV_ASSUMPTION,
                "시나리오 배수는 일반적인 민감도 가정이며 산업별 근거가 아님",
            ],
        },
        metrics=result.metrics.model_dump(),
        issues=result.issues,
        warnings=result.warnings,
        confidence=round(confidence, 4),
    )


def run_scenarios(inputs: FinancialInputs, base_confidence: float = 0.5) -> list[ScenarioResult]:
    """Conservative / Base / Optimistic 3개 시나리오를 순서대로 반환"""
    return [run_scenario(inputs, name, base_confidence) for name in ScenarioName]

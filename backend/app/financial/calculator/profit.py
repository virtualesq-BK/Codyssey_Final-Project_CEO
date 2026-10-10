"""
Gross Profit = Revenue - Variable Cost
Gross Margin = Gross Profit / Revenue
"""
from __future__ import annotations

from typing import Any

from app.financial.calculator.errors import InvalidInputError, UndefinedResultError
from app.financial.calculator.validation import require_number


def calculate_variable_cost(variable_cost_per_unit: Any, customers: Any) -> float:
    """총 변동비 = 고객 1인당 변동비 × 고객 수"""
    unit_cost = require_number("variable_cost_per_unit", variable_cost_per_unit)
    c = require_number("customers", customers)
    return unit_cost * c


def calculate_gross_profit(revenue: Any, variable_cost: Any) -> float:
    """매출총이익. 변동비가 매출보다 크면 음수가 될 수 있다."""
    r = require_number("revenue", revenue)
    vc = require_number("variable_cost", variable_cost)
    return r - vc


def calculate_operating_profit(gross_profit: Any, fixed_cost: Any) -> float:
    """월 영업이익 = 매출총이익 - 고정비. 음수(손실)일 수 있다."""
    gp = require_number("gross_profit", gross_profit, min_value=None)
    fc = require_number("fixed_cost", fixed_cost)
    return gp - fc


def calculate_gross_margin(gross_profit: Any, revenue: Any) -> float:
    """매출총이익률 (0.4 = 40%). 매출이 0이면 정의되지 않는다."""
    gp = require_number("gross_profit", gross_profit, min_value=None)
    r = require_number("revenue", revenue)
    if r == 0:
        raise UndefinedResultError("revenue", "매출이 0이면 매출총이익률을 계산할 수 없습니다")
    if gp > r:
        raise InvalidInputError("gross_profit", "매출총이익이 매출보다 클 수 없습니다")
    return gp / r

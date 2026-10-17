"""
Break-even Point
단위당 기여이익 = Price - Variable Cost per Unit
BEP 고객 수   = Fixed Cost / 단위당 기여이익 (올림)
BEP 매출      = BEP 고객 수 × Price
"""
from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel

from app.financial.calculator.errors import UndefinedResultError
from app.financial.calculator.validation import require_number


class BreakEvenResult(BaseModel):
    unit_contribution: float
    breakeven_units: int
    breakeven_revenue: float


def calculate_unit_contribution(price: Any, variable_cost_per_unit: Any) -> float:
    """단위당 기여이익. 음수일 수 있다."""
    p = require_number("price", price)
    vc = require_number("variable_cost_per_unit", variable_cost_per_unit)
    return p - vc


def calculate_breakeven(fixed_cost: Any, price: Any, variable_cost_per_unit: Any) -> BreakEvenResult:
    """손익분기점. 단위당 기여이익이 0 이하이면 도달할 수 없으므로 예외를 발생시킨다."""
    fc = require_number("fixed_cost", fixed_cost)
    contribution = calculate_unit_contribution(price, variable_cost_per_unit)
    if contribution <= 0:
        raise UndefinedResultError(
            "unit_contribution",
            f"단위당 기여이익이 0 이하({contribution:g})이면 손익분기점에 도달할 수 없습니다",
        )
    units = math.ceil(fc / contribution)
    return BreakEvenResult(
        unit_contribution=contribution,
        breakeven_units=units,
        breakeven_revenue=units * float(price),
    )

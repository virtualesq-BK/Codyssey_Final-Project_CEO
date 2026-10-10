"""
CAC = Customer Acquisition Cost / New Customers
"""
from __future__ import annotations

from typing import Any

from app.financial.calculator.errors import UndefinedResultError
from app.financial.calculator.validation import require_number


def calculate_cac(acquisition_cost: Any, new_customers: Any) -> float:
    """고객 획득 단가. 신규 고객이 0이면 정의되지 않는다."""
    cost = require_number("acquisition_cost", acquisition_cost)
    n = require_number("new_customers", new_customers)
    if n == 0:
        raise UndefinedResultError("new_customers", "신규 고객이 0이면 CAC를 계산할 수 없습니다")
    return cost / n

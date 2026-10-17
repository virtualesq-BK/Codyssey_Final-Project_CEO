"""
Revenue = Price × Customers
"""
from __future__ import annotations

from typing import Any

from app.financial.calculator.validation import require_number


def calculate_revenue(price: Any, customers: Any) -> float:
    """
    월 매출. price 는 고객 1인당 월 결제액, customers 는 월 결제 고객 수.
    price 또는 customers 가 0이면 매출 0을 반환한다 (유효한 계산 결과).
    """
    p = require_number("price", price)
    c = require_number("customers", customers)
    return p * c

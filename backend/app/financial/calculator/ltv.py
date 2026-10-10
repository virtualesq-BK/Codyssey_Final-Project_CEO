"""
LTV = ARPU × Gross Margin / Monthly Churn Rate
LTV/CAC = LTV / CAC

가정: 고객당 월 결제액(ARPU)과 이탈률이 기간 내내 일정하다.
      평균 고객 유지 기간 = 1 / 월 이탈률 (개월)
"""
from __future__ import annotations

from typing import Any

from app.financial.calculator.errors import UndefinedResultError
from app.financial.calculator.validation import require_number, require_rate

LTV_ASSUMPTION = "ARPU와 월 이탈률이 일정하며 평균 유지 기간은 1/월 이탈률(개월)이라고 가정"


def calculate_ltv(arpu: Any, gross_margin: Any, monthly_churn_rate: Any) -> float:
    """고객 생애 가치. 이탈률이 0이면 유지 기간이 무한대가 되어 정의되지 않는다."""
    a = require_number("arpu", arpu)
    # 변동비가 매출보다 크면 margin 이 음수일 수 있다 (하한 없음, 상한 1)
    margin = require_number("gross_margin", gross_margin, min_value=None, max_value=1.0)
    churn = require_rate("monthly_churn_rate", monthly_churn_rate)
    if churn == 0:
        raise UndefinedResultError(
            "monthly_churn_rate", "이탈률이 0이면 LTV가 무한대가 되어 계산할 수 없습니다"
        )
    return a * margin / churn


def calculate_ltv_cac_ratio(ltv: Any, cac: Any) -> float:
    """LTV/CAC 배수. CAC가 0이면 정의되지 않는다."""
    l = require_number("ltv", ltv, min_value=None)
    c = require_number("cac", cac)
    if c == 0:
        raise UndefinedResultError("cac", "CAC가 0이면 LTV/CAC를 계산할 수 없습니다")
    return l / c

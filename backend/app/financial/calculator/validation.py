"""
입력값 검증 – 모든 calculator 함수가 공통으로 사용
"""
from __future__ import annotations

import math
from typing import Any, Optional

from app.financial.calculator.errors import InvalidInputError, MissingInputError

# 이 값을 넘는 금액/수량은 입력 오류로 간주한다 (1경)
MAX_REALISTIC_VALUE: float = 1e16


def require_number(
    field: str,
    value: Any,
    *,
    min_value: Optional[float] = 0.0,
    max_value: float = MAX_REALISTIC_VALUE,
    allow_zero: bool = True,
) -> float:
    """value 를 검증하여 float 로 반환. 실패 시 CalculationError 계열 예외 발생"""
    if value is None:
        raise MissingInputError(field, "값이 없습니다")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInputError(field, f"숫자가 아닙니다 ({value!r})")

    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise InvalidInputError(field, "NaN 또는 무한대는 허용되지 않습니다")
    if min_value is not None and number < min_value:
        raise InvalidInputError(field, f"{min_value:g} 이상이어야 합니다 (입력: {number:g})")
    if not allow_zero and number == 0:
        raise InvalidInputError(field, "0은 허용되지 않습니다")
    if number > max_value:
        raise InvalidInputError(field, f"비현실적으로 큰 값입니다 (입력: {number:g}, 상한: {max_value:g})")
    return number


def require_rate(field: str, value: Any) -> float:
    """0~1 사이 비율 검증"""
    return require_number(field, value, min_value=0.0, max_value=1.0)

"""
Financial Calculator 예외
계산 불가 상황을 NaN/0 으로 조용히 반환하지 않고 명시적으로 알린다
"""
from __future__ import annotations


class CalculationError(ValueError):
    """모든 재무 계산 오류의 기반 클래스"""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class MissingInputError(CalculationError):
    """계산에 필요한 입력값이 없음"""


class InvalidInputError(CalculationError):
    """입력값이 숫자가 아니거나 허용 범위를 벗어남"""


class UndefinedResultError(CalculationError):
    """입력은 유효하지만 결과가 정의되지 않음 (0으로 나누기 등)"""

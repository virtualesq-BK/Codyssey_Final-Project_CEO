"""
Risk Taxonomy 및 Risk Scoring
Risk Score = Likelihood(1~5) × Impact(1~5) – 점수 계산은 LLM 이 아닌 Python 이 수행한다
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

SCALE_MIN: int = 1
SCALE_MAX: int = 5

INSUFFICIENT_EVIDENCE = "근거 부족 / 추가 검토 필요"
REGULATORY_REVIEW_REQUIRED = "규제 검토 필요"
DEFAULT_MITIGATION = "대응 방안 수립 필요"
REGULATORY_MITIGATION = "관련 법령·인허가 요건을 전문가 또는 소관 기관에 확인"


class RiskCategory(str, Enum):
    MARKET = "market"
    COMPETITION = "competition"
    TECHNOLOGY = "technology"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    EXECUTION = "execution"


CATEGORY_LABELS: dict[RiskCategory, str] = {
    RiskCategory.MARKET: "Market Risk",
    RiskCategory.COMPETITION: "Competition Risk",
    RiskCategory.TECHNOLOGY: "Technology Risk",
    RiskCategory.FINANCIAL: "Financial Risk",
    RiskCategory.REGULATORY: "Regulatory Risk",
    RiskCategory.EXECUTION: "Execution Risk",
}


class RiskLevel(str, Enum):
    LOW = "low"            # 1~4
    MEDIUM = "medium"      # 5~9
    HIGH = "high"          # 10~16
    CRITICAL = "critical"  # 17~25
    UNKNOWN = "unknown"    # 평가 불가


def normalize_scale(value: Any) -> Optional[int]:
    """1~5 정수 척도로 변환. 범위를 벗어나거나 숫자가 아니면 None (평가 불가)"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != int(value):
        return None
    number = int(value)
    return number if SCALE_MIN <= number <= SCALE_MAX else None


def calculate_risk_score(likelihood: int, impact: int) -> int:
    for name, value in (("likelihood", likelihood), ("impact", impact)):
        if normalize_scale(value) is None:
            raise ValueError(f"{name} 은(는) {SCALE_MIN}~{SCALE_MAX} 사이 정수여야 합니다 (입력: {value!r})")
    return int(likelihood) * int(impact)


def classify_risk_level(score: Optional[int]) -> RiskLevel:
    if score is None:
        return RiskLevel.UNKNOWN
    if score >= 17:
        return RiskLevel.CRITICAL
    if score >= 10:
        return RiskLevel.HIGH
    if score >= 5:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class RiskItem(BaseModel):
    category: RiskCategory
    label: str = ""
    risk: str
    evidence: list[str] = Field(default_factory=list)
    likelihood: Optional[int] = Field(default=None, ge=SCALE_MIN, le=SCALE_MAX)
    impact: Optional[int] = Field(default=None, ge=SCALE_MIN, le=SCALE_MAX)
    score: Optional[int] = None
    level: RiskLevel = RiskLevel.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    mitigation: str = DEFAULT_MITIGATION
    needs_review: bool = False

    @model_validator(mode="after")
    def _derive(self) -> "RiskItem":
        # label·score·level 은 입력값과 무관하게 항상 다시 계산한다
        self.label = CATEGORY_LABELS[self.category]
        if self.likelihood is not None and self.impact is not None:
            self.score = calculate_risk_score(self.likelihood, self.impact)
        else:
            self.score = None
            self.needs_review = True
        self.level = classify_risk_level(self.score)
        return self


def insufficient_evidence_item(category: RiskCategory) -> RiskItem:
    """평가 근거가 없는 category 를 위한 항목 – 위험을 지어내지 않는다"""
    regulatory = category == RiskCategory.REGULATORY
    return RiskItem(
        category=category,
        risk=REGULATORY_REVIEW_REQUIRED if regulatory else INSUFFICIENT_EVIDENCE,
        mitigation=REGULATORY_MITIGATION if regulatory else DEFAULT_MITIGATION,
        needs_review=True,
    )

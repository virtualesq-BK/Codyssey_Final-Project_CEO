"""
Risk Agent
6개 taxonomy 별 위험을 구조화하여 반환한다

LLM 은 위험 식별과 Likelihood/Impact 판단만 담당하고,
Risk Score 계산·등급 분류·근거 부족 처리·규제 검토 표시는 Python 이 수행한다.
법률 자문이 아니라 사업상 위험 신호와 검토 필요성을 제시하는 의사결정 지원이다.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.base_agent import BaseAgent
from app.core.llm_provider import LLMProvider
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea, Evidence
from app.risk.evidence import NullRiskEvidenceProvider, RiskEvidenceProvider
from app.risk.taxonomy import (
    CATEGORY_LABELS,
    DEFAULT_MITIGATION,
    REGULATORY_MITIGATION,
    REGULATORY_REVIEW_REQUIRED,
    RiskCategory,
    RiskItem,
    insufficient_evidence_item,
    normalize_scale,
)

logger = logging.getLogger(__name__)

# LLM 이 confidence 를 주지 않았을 때의 기본값
DEFAULT_ITEM_CONFIDENCE: float = 0.3
# 근거(evidence)가 없는 위험의 confidence 상한
NO_EVIDENCE_CONFIDENCE_CAP: float = 0.4
# 출처 없는 규제 위험의 confidence 상한
UNSOURCED_REGULATORY_CONFIDENCE_CAP: float = 0.3
TOP_RISK_COUNT: int = 3

SCORING_RULE = "Risk Score = Likelihood(1~5) × Impact(1~5)"

_SYSTEM_PROMPT = """당신은 예비창업자의 사업 아이디어에서 위험 신호를 식별하는 리스크 분석가입니다.

규칙:
1. category 는 market / competition / technology / financial / regulatory / execution 중 하나만 사용하라.
2. likelihood 와 impact 는 1~5 정수로 평가하라. 판단할 근거가 없으면 null 로 두라.
3. evidence 에는 사업 아이디어 설명 또는 제공된 참고 근거에서 확인되는 내용만 적어라.
4. 확인되지 않은 법률·규정·인허가 요건을 사실처럼 쓰지 마라. 특정 법령명이나 조항을 지어내지 마라.
5. 근거가 없는 category 는 출력하지 마라.
6. score 는 계산하지 마라.
"""


class RiskDraft(BaseModel):
    """LLM 출력 초안 – 값 검증과 정규화는 Python 에서 수행한다"""

    category: Any = None
    risk: Any = None
    evidence: Any = None
    likelihood: Any = None
    impact: Any = None
    confidence: Any = None
    mitigation: Any = None


class RiskAssessmentDraft(BaseModel):
    risks: list[RiskDraft] = Field(default_factory=list)


def parse_category(value: Any) -> Optional[RiskCategory]:
    if not isinstance(value, str):
        return None
    key = value.strip().lower().replace("_", " ")
    if key.endswith(" risk"):
        key = key[: -len(" risk")]
    try:
        return RiskCategory(key.strip())
    except ValueError:
        return None


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]


def _as_confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT_ITEM_CONFIDENCE
    if not 0.0 <= value <= 1.0:
        return DEFAULT_ITEM_CONFIDENCE
    return float(value)


class RiskAgent(BaseAgent):
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        agent_name: Optional[str] = None,
        evidence_provider: Optional[RiskEvidenceProvider] = None,
    ):
        super().__init__(llm_provider=llm_provider, agent_name=agent_name)
        self._evidence: RiskEvidenceProvider = evidence_provider or NullRiskEvidenceProvider()

    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        sourced = await self._collect_evidence(idea)
        drafts = await self._identify_risks(idea, sourced)

        items: list[RiskItem] = []
        for draft in drafts:
            item = self._build_item(draft, sourced)
            if item is not None:
                items.append(item)

        # 평가되지 않은 category 는 위험을 지어내지 않고 근거 부족으로 표시한다
        covered = {item.category for item in items}
        insufficient = [c for c in RiskCategory if c not in covered]
        items.extend(insufficient_evidence_item(c) for c in insufficient)
        items.sort(key=lambda r: list(RiskCategory).index(r.category))

        scored = [r for r in items if r.score is not None]
        top = sorted(scored, key=lambda r: r.score or 0, reverse=True)[:TOP_RISK_COUNT]
        regulatory_review = any(
            r.category == RiskCategory.REGULATORY and r.needs_review for r in items
        )
        scored_categories = {r.category for r in scored}

        findings: list[dict[str, Any]] = [
            {"scoring_rule": SCORING_RULE},
            {"risks": [r.model_dump(mode="json") for r in items]},
            {
                "top_risks": [
                    {"label": r.label, "risk": r.risk, "score": r.score, "level": r.level.value}
                    for r in top
                ]
            },
            {
                "risk_summary": {
                    "scored_count": len(scored),
                    "max_score": max((r.score or 0 for r in scored), default=None),
                    "average_score": (
                        round(sum(r.score or 0 for r in scored) / len(scored), 2) if scored else None
                    ),
                }
            },
            {"insufficient_evidence": [CATEGORY_LABELS[c] for c in insufficient]},
            {"regulatory_review_required": regulatory_review},
        ]

        recommendations = [f"[{r.label}] {r.mitigation}" for r in top]
        if regulatory_review:
            recommendations.append(f"[Regulatory Risk] {REGULATORY_REVIEW_REQUIRED}: {REGULATORY_MITIGATION}")
        if insufficient:
            labels = ", ".join(CATEGORY_LABELS[c] for c in insufficient)
            recommendations.append(f"근거 부족으로 평가하지 못한 영역 추가 조사 필요: {labels}")

        if top:
            summary = (
                f"{len(RiskCategory)}개 영역 중 {len(scored_categories)}개 영역의 위험을 평가했습니다. "
                f"최고 위험은 {top[0].label} (score {top[0].score}, {top[0].level.value})입니다."
            )
        else:
            summary = "위험을 평가할 근거가 부족합니다. 근거 부족 / 추가 검토 필요."
        if regulatory_review:
            summary += f" {REGULATORY_REVIEW_REQUIRED}."

        all_scored = len(scored_categories) == len(RiskCategory)
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS if all_scored else AgentStatus.PARTIAL,
            summary=summary,
            findings=findings,
            evidence=[e for evidences in sourced.values() for e in evidences],
            recommendations=recommendations,
            confidence=round(sum(r.confidence for r in items) / len(items), 2),
        )

    async def _collect_evidence(self, idea: BusinessIdea) -> dict[RiskCategory, list[Evidence]]:
        async def fetch(category: RiskCategory) -> list[Evidence]:
            try:
                return list(await self._evidence.get_evidence(idea, category))
            except Exception as exc:
                logger.warning("[%s] %s 근거 조회 실패: %s", self.agent_name, category.value, exc)
                return []

        categories = list(RiskCategory)
        results = await asyncio.gather(*(fetch(c) for c in categories))
        return dict(zip(categories, results))

    async def _identify_risks(
        self, idea: BusinessIdea, sourced: dict[RiskCategory, list[Evidence]]
    ) -> list[RiskDraft]:
        references = {
            category.value: [{"title": e.title, "source": e.source, "content": e.content} for e in evidences]
            for category, evidences in sourced.items()
            if evidences
        }
        prompt = f"""다음 사업 아이디어의 위험을 식별하라.

## 사업 아이디어
- 제목: {idea.title}
- 문제: {idea.problem}
- 고객: {idea.customer}
- 솔루션: {idea.solution}
- 산업: {idea.industry}
- 지역: {idea.location}
- 단계: {idea.business_stage.value}

## 참고 근거 (출처 확인됨)
{json.dumps(references, ensure_ascii=False, indent=2) if references else '없음'}

반드시 아래 JSON 형식으로만 응답하라:
{{
  "risks": [
    {{
      "category": "market|competition|technology|financial|regulatory|execution",
      "risk": "위험 내용",
      "evidence": ["판단 근거"],
      "likelihood": 1~5 또는 null,
      "impact": 1~5 또는 null,
      "confidence": 0.0~1.0,
      "mitigation": "대응 방안"
    }}
  ]
}}"""
        try:
            draft = await self.llm.generate_structured(prompt, RiskAssessmentDraft, system=_SYSTEM_PROMPT)
            return draft.risks
        except Exception as exc:
            logger.warning("[%s] 위험 식별 실패, 근거 부족으로 처리: %s", self.agent_name, exc)
            return []

    def _build_item(
        self, draft: RiskDraft, sourced: dict[RiskCategory, list[Evidence]]
    ) -> Optional[RiskItem]:
        category = parse_category(draft.category)
        risk = _as_text(draft.risk)
        if category is None or not risk:
            logger.warning("[%s] 잘못된 위험 항목 제외: category=%r", self.agent_name, draft.category)
            return None

        evidence = _as_text_list(draft.evidence)
        confidence = _as_confidence(draft.confidence)
        mitigation = _as_text(draft.mitigation) or DEFAULT_MITIGATION
        needs_review = False

        if not evidence:
            confidence = min(confidence, NO_EVIDENCE_CONFIDENCE_CAP)

        # 출처 없는 규제 내용은 사실로 취급하지 않는다
        if category == RiskCategory.REGULATORY and not sourced.get(category):
            risk = f"{REGULATORY_REVIEW_REQUIRED} (미확인): {risk}"
            confidence = min(confidence, UNSOURCED_REGULATORY_CONFIDENCE_CAP)
            if REGULATORY_MITIGATION not in mitigation:
                mitigation = (
                    REGULATORY_MITIGATION
                    if mitigation == DEFAULT_MITIGATION
                    else f"{mitigation} / {REGULATORY_MITIGATION}"
                )
            needs_review = True

        return RiskItem(
            category=category,
            risk=risk,
            evidence=evidence,
            likelihood=normalize_scale(draft.likelihood),
            impact=normalize_scale(draft.impact),
            confidence=confidence,
            mitigation=mitigation,
            needs_review=needs_review,
        )

"""
Risk taxonomy / Risk Agent tests – schema 와 점수 계산을 검증한다
"""
import json

import pytest
from pydantic import ValidationError

from app.agents.risk_agent import RiskAgent, parse_category
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentStatus, BusinessIdea, Evidence
from app.risk.taxonomy import (
    CATEGORY_LABELS,
    DEFAULT_MITIGATION,
    INSUFFICIENT_EVIDENCE,
    REGULATORY_MITIGATION,
    REGULATORY_REVIEW_REQUIRED,
    RiskCategory,
    RiskItem,
    RiskLevel,
    calculate_risk_score,
    classify_risk_level,
    insufficient_evidence_item,
    normalize_scale,
)

ALL_CATEGORIES = ["market", "competition", "technology", "financial", "regulatory", "execution"]
REQUIRED_KEYS = {"category", "label", "risk", "evidence", "likelihood", "impact", "score", "level", "confidence", "mitigation"}


def make_idea() -> BusinessIdea:
    return BusinessIdea(
        idea_id="risk-001",
        title="배달 세탁 구독",
        problem="바쁜 직장인이 세탁소 방문 시간 없음",
        customer="25-40대 직장인",
        solution="앱으로 픽업·배달 세탁 서비스",
        industry="생활서비스",
    )


def draft(category: str, **overrides) -> dict:
    data = {
        "category": category,
        "risk": f"{category} 위험",
        "evidence": [f"{category} 근거"],
        "likelihood": 3,
        "impact": 4,
        "confidence": 0.6,
        "mitigation": f"{category} 대응",
    }
    data.update(overrides)
    return data


def make_agent(risks: list[dict], **kwargs) -> RiskAgent:
    llm = MockProvider()
    llm.set_responses([json.dumps({"risks": risks}, ensure_ascii=False)])
    return RiskAgent(llm_provider=llm, **kwargs)


def finding(result, key):
    return next(f[key] for f in result.findings if key in f)


def risk_of(result, category: str) -> dict:
    return next(r for r in finding(result, "risks") if r["category"] == category)


class StubEvidenceProvider:
    def __init__(self, by_category: dict):
        self.by_category = by_category

    async def get_evidence(self, idea, category):
        return self.by_category.get(category, [])


# ── Taxonomy / Scoring ───────────────────────────────

def test_taxonomy_has_six_categories():
    assert [c.value for c in RiskCategory] == ALL_CATEGORIES
    assert set(CATEGORY_LABELS) == set(RiskCategory)
    assert CATEGORY_LABELS[RiskCategory.REGULATORY] == "Regulatory Risk"


@pytest.mark.parametrize("likelihood, impact, expected", [(1, 1, 1), (3, 4, 12), (5, 5, 25)])
def test_risk_score(likelihood, impact, expected):
    assert calculate_risk_score(likelihood, impact) == expected


@pytest.mark.parametrize("likelihood, impact", [(0, 3), (6, 3), (3, 0), (3, 6), (2.5, 3), (None, 3)])
def test_risk_score_rejects_out_of_scale(likelihood, impact):
    with pytest.raises(ValueError):
        calculate_risk_score(likelihood, impact)


@pytest.mark.parametrize(
    "score, level",
    [(1, "low"), (4, "low"), (5, "medium"), (9, "medium"), (10, "high"), (16, "high"), (20, "critical"), (25, "critical"), (None, "unknown")],
)
def test_risk_level(score, level):
    assert classify_risk_level(score) == RiskLevel(level)


@pytest.mark.parametrize("value, expected", [(3, 3), (5.0, 5), (0, None), (6, None), (2.5, None), ("3", None), (True, None), (None, None)])
def test_normalize_scale(value, expected):
    assert normalize_scale(value) == expected


def test_risk_item_recomputes_score_and_level():
    item = RiskItem(category=RiskCategory.MARKET, risk="수요 불확실", likelihood=4, impact=5, score=1, level=RiskLevel.LOW)
    assert item.score == 20
    assert item.level == RiskLevel.CRITICAL
    assert item.label == "Market Risk"
    assert item.needs_review is False


def test_risk_item_without_scale_is_unscored_and_needs_review():
    item = RiskItem(category=RiskCategory.MARKET, risk="수요 불확실", likelihood=4)
    assert item.score is None
    assert item.level == RiskLevel.UNKNOWN
    assert item.needs_review is True


def test_risk_item_rejects_out_of_range_scale():
    with pytest.raises(ValidationError):
        RiskItem(category=RiskCategory.MARKET, risk="x", likelihood=7, impact=1)


def test_insufficient_evidence_item():
    item = insufficient_evidence_item(RiskCategory.TECHNOLOGY)
    assert item.risk == INSUFFICIENT_EVIDENCE
    assert item.score is None and item.confidence == 0.0 and item.needs_review

    regulatory = insufficient_evidence_item(RiskCategory.REGULATORY)
    assert regulatory.risk == REGULATORY_REVIEW_REQUIRED
    assert regulatory.mitigation == REGULATORY_MITIGATION


@pytest.mark.parametrize(
    "raw, expected",
    [("market", "market"), ("Market Risk", "market"), ("REGULATORY_RISK", "regulatory"), (" execution ", "execution"), ("legal", None), (3, None)],
)
def test_parse_category(raw, expected):
    parsed = parse_category(raw)
    assert (parsed.value if parsed else None) == expected


# ── Risk Agent ───────────────────────────────────────

async def test_structured_output_covers_all_categories():
    agent = make_agent([draft(c) for c in ALL_CATEGORIES])
    result = await agent.run(make_idea())

    assert result.agent_name == "RiskAgent"
    assert result.status == AgentStatus.SUCCESS
    risks = finding(result, "risks")
    assert [r["category"] for r in risks] == ALL_CATEGORIES
    for r in risks:
        assert REQUIRED_KEYS <= r.keys()
        assert r["score"] == 12
        assert r["level"] == "high"
    json.dumps(result.findings, ensure_ascii=False)


async def test_score_is_computed_by_python_not_llm():
    agent = make_agent([draft("market", likelihood=2, impact=5, score=99, level="low")])
    result = await agent.run(make_idea())
    market = risk_of(result, "market")
    assert market["score"] == 10
    assert market["level"] == "high"


async def test_top_risks_sorted_by_score():
    agent = make_agent([
        draft("market", likelihood=2, impact=2),
        draft("competition", likelihood=5, impact=5),
        draft("technology", likelihood=3, impact=3),
        draft("execution", likelihood=4, impact=4),
    ])
    result = await agent.run(make_idea())
    top = finding(result, "top_risks")
    assert [t["score"] for t in top] == [25, 16, 9]
    assert top[0]["label"] == "Competition Risk"
    assert finding(result, "risk_summary") == {"scored_count": 4, "max_score": 25, "average_score": 13.5}
    assert result.recommendations[0] == "[Competition Risk] competition 대응"


async def test_mitigation_always_present():
    agent = make_agent([draft("market", mitigation=None), draft("execution", mitigation="  ")])
    result = await agent.run(make_idea())
    for r in finding(result, "risks"):
        assert r["mitigation"].strip()
    assert risk_of(result, "market")["mitigation"] == DEFAULT_MITIGATION


async def test_insufficient_evidence_categories_are_not_invented():
    agent = make_agent([draft("market")])
    result = await agent.run(make_idea())

    assert result.status == AgentStatus.PARTIAL
    assert len(finding(result, "risks")) == 6
    technology = risk_of(result, "technology")
    assert technology["risk"] == INSUFFICIENT_EVIDENCE
    assert technology["score"] is None
    assert technology["level"] == "unknown"
    assert technology["confidence"] == 0.0
    assert "Technology Risk" in finding(result, "insufficient_evidence")
    assert "Market Risk" not in finding(result, "insufficient_evidence")


async def test_llm_failure_returns_all_insufficient():
    llm = MockProvider()
    llm.set_responses(["JSON 이 아닌 응답"])
    result = await RiskAgent(llm_provider=llm).run(make_idea())

    assert result.status == AgentStatus.PARTIAL
    assert result.error_message is None
    assert result.confidence == 0.0
    assert finding(result, "top_risks") == []
    assert len(finding(result, "insufficient_evidence")) == 6
    assert all(r["score"] is None for r in finding(result, "risks"))


async def test_unsourced_regulatory_risk_is_marked_for_review():
    agent = make_agent([draft("regulatory", risk="세탁업 신고가 필요함", confidence=0.9)])
    result = await agent.run(make_idea())

    regulatory = risk_of(result, "regulatory")
    assert regulatory["risk"].startswith(REGULATORY_REVIEW_REQUIRED)
    assert "미확인" in regulatory["risk"]
    assert regulatory["needs_review"] is True
    assert regulatory["confidence"] <= 0.3
    assert REGULATORY_MITIGATION in regulatory["mitigation"]
    assert finding(result, "regulatory_review_required") is True
    assert REGULATORY_REVIEW_REQUIRED in result.summary


async def test_missing_regulatory_category_requires_review():
    agent = make_agent([draft("market")])
    result = await agent.run(make_idea())
    assert risk_of(result, "regulatory")["risk"] == REGULATORY_REVIEW_REQUIRED
    assert finding(result, "regulatory_review_required") is True


async def test_sourced_regulatory_risk_is_kept_and_evidence_linked():
    source = Evidence(title="세탁업 관련 고시", source="법제처", url="https://example.org", content="신고 대상", confidence=0.9)
    provider = StubEvidenceProvider({RiskCategory.REGULATORY: [source]})
    agent = make_agent([draft("regulatory", risk="세탁업 신고 대상 여부", confidence=0.8)], evidence_provider=provider)
    result = await agent.run(make_idea())

    regulatory = risk_of(result, "regulatory")
    assert regulatory["risk"] == "세탁업 신고 대상 여부"
    assert regulatory["needs_review"] is False
    assert regulatory["confidence"] == 0.8
    assert finding(result, "regulatory_review_required") is False
    assert result.evidence == [source]


async def test_invalid_scale_becomes_unscored():
    agent = make_agent([draft("market", likelihood=9, impact="high")])
    result = await agent.run(make_idea())
    market = risk_of(result, "market")
    assert market["likelihood"] is None and market["impact"] is None
    assert market["score"] is None
    assert market["needs_review"] is True
    assert result.status == AgentStatus.PARTIAL


async def test_unknown_category_and_empty_risk_are_dropped():
    agent = make_agent([draft("legal"), draft("market", risk="")])
    result = await agent.run(make_idea())
    assert len(finding(result, "risks")) == 6
    assert len(finding(result, "insufficient_evidence")) == 6


async def test_confidence_capped_without_evidence():
    agent = make_agent([draft("market", evidence=[], confidence=0.95)])
    result = await agent.run(make_idea())
    assert risk_of(result, "market")["confidence"] == 0.4


async def test_evidence_provider_failure_is_tolerated():
    class Broken:
        async def get_evidence(self, idea, category):
            raise RuntimeError("RAG down")

    agent = make_agent([draft("market")], evidence_provider=Broken())
    result = await agent.run(make_idea())
    assert risk_of(result, "market")["score"] == 12
    assert result.evidence == []


# ── Integration ──────────────────────────────────────

async def test_orchestrator_uses_real_financial_and_risk_agents():
    from app.agents.financial_agent import FinancialAgent
    from app.agents.orchestrator import Orchestrator

    mock = MockProvider()
    mock.set_responses([
        '{"summary":"ok","strengths":[],"weaknesses":[],"opportunities":[],'
        '"risks":[],"financial_summary":"미확정","validation_items":[],'
        '"action_plan":[],"decision":"VALIDATE_MORE","confidence":0.5}'
    ])
    orchestrator = Orchestrator(llm_provider=mock)
    assert isinstance(orchestrator.agents["FinancialAgent"], FinancialAgent)
    assert isinstance(orchestrator.agents["RiskAgent"], RiskAgent)

    result = await orchestrator.run(make_idea())
    assert len(result.agent_results) == 6
    assert result.agent_results["FinancialAgent"].status == AgentStatus.PARTIAL
    assert result.agent_results["RiskAgent"].status == AgentStatus.PARTIAL
    assert result.decision_result is not None

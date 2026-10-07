"""
Schema validation tests
"""
import pytest
from pydantic import ValidationError

from app.core.schemas import (
    AgentResult,
    AgentStatus,
    BusinessIdea,
    BusinessStage,
    Decision,
    DecisionResult,
    Evidence,
    UserProfile,
)


def make_idea(**kwargs) -> BusinessIdea:
    defaults = dict(
        idea_id="test-001",
        title="테스트 카페",
        problem="동네에 카페가 없다",
        customer="20-30대 직장인",
        solution="품질 좋은 원두 커피 제공",
        industry="식음료",
        location="서울",
    )
    defaults.update(kwargs)
    return BusinessIdea(**defaults)


class TestBusinessIdea:
    def test_valid(self):
        idea = make_idea()
        assert idea.idea_id == "test-001"
        assert idea.business_stage == BusinessStage.IDEA

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            make_idea(title="")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            make_idea(title="   ")

    def test_with_user_profile(self):
        profile = UserProfile(name="홍길동", capital=5000.0)
        idea = make_idea(user_profile=profile)
        assert idea.user_profile.name == "홍길동"

    def test_strip_whitespace(self):
        idea = make_idea(title="  카페  ")
        assert idea.title == "카페"


class TestEvidence:
    def test_valid(self):
        ev = Evidence(title="통계", source="통계청", content="시장 조사 데이터", confidence=0.8)
        assert ev.confidence == 0.8

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            Evidence(title="x", source="x", content="x", confidence=1.5)

    def test_confidence_negative(self):
        with pytest.raises(ValidationError):
            Evidence(title="x", source="x", content="x", confidence=-0.1)


class TestAgentResult:
    def test_valid(self):
        r = AgentResult(
            agent_name="MarketAgent",
            status=AgentStatus.SUCCESS,
            summary="분석 완료",
            confidence=0.7,
        )
        assert r.status == AgentStatus.SUCCESS

    def test_factory_failed(self):
        r = AgentResult.failed("MarketAgent", "timeout")
        assert r.status == AgentStatus.FAILED
        assert "timeout" in r.error_message

    def test_factory_skipped(self):
        r = AgentResult.skipped("MarketAgent", "의존성 실패")
        assert r.status == AgentStatus.SKIPPED

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            AgentResult(
                agent_name="X", status=AgentStatus.SUCCESS, summary="x", confidence=2.0
            )


class TestDecisionResult:
    def test_valid(self):
        r = DecisionResult(
            summary="테스트 결론",
            decision=Decision.GO,
            confidence=0.8,
        )
        assert r.decision == Decision.GO
        assert "보장하지 않습니다" in r.disclaimer

    def test_decision_values(self):
        for d in Decision:
            r = DecisionResult(summary="x", decision=d, confidence=0.5)
            assert r.decision == d

"""
Interview Agent tests – LLM mock 사용
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.agents.interview_agent import (
    MAX_QUESTIONS,
    Coverage,
    InterviewAgent,
    InterviewMessage,
)
from app.api.main import app
from app.core.llm_provider import MockProvider

MEMO = "다문화 아이 한국어 앱"


def turn_json(**overrides) -> str:
    data = {
        "message": "어떤 서비스인지 편하게 말해주세요.",
        "quick_replies": ["아직 정한 게 없어요"],
        "covered": {"idea": "empty", "customer": "empty", "alternative": "empty", "payer": "empty", "context": "empty"},
        "done": False,
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


@pytest.mark.asyncio
async def test_next_turn_parses_and_trims_quick_replies():
    llm = MockProvider()
    llm.set_responses([turn_json(quick_replies=["a", " ", "b", "c", "d"])])
    turn = await InterviewAgent(llm_provider=llm).next_turn(MEMO, [])
    assert turn.message.startswith("어떤 서비스")
    assert turn.quick_replies == ["a", "b", "c"]
    assert turn.done is False


@pytest.mark.asyncio
async def test_next_turn_retries_once_on_broken_json():
    llm = MockProvider()
    llm.set_responses(["not json", turn_json()])
    turn = await InterviewAgent(llm_provider=llm).next_turn(MEMO, [])
    assert turn.message
    assert len(llm.get_usages()) == 2


@pytest.mark.asyncio
async def test_next_turn_reads_json_with_surrounding_text():
    # 실제로 모델이 JSON 앞에 질문 문장을 붙여 보낸 경우
    llm = MockProvider()
    llm.set_responses(["어떤 장면이었는지 궁금해요.\n```json\n" + turn_json() + "\n```\n이상입니다."])
    turn = await InterviewAgent(llm_provider=llm).next_turn(MEMO, [])
    assert turn.message.startswith("어떤 서비스")
    assert len(llm.get_usages()) == 1


@pytest.mark.asyncio
async def test_next_turn_stops_at_question_limit_without_llm_call():
    llm = MockProvider()
    messages = []
    for i in range(MAX_QUESTIONS):
        messages += [
            InterviewMessage(role="assistant", content=f"질문 {i}"),
            InterviewMessage(role="user", content=f"답 {i}"),
        ]
    prev = Coverage(idea="filled", customer="filled")
    turn = await InterviewAgent(llm_provider=llm).next_turn(MEMO, messages, prev)
    assert turn.done is True
    assert turn.covered == prev
    assert llm.get_usages() == []


@pytest.mark.asyncio
async def test_draft_profile_normalizes_location_and_strips():
    llm = MockProvider()
    llm.set_responses([
        json.dumps({
            "name": "  한국어 친구 ",
            "one_liner": "교과 어휘로 수업을 따라가게 돕는 앱",
            "industry": "에듀테크",
            "location": "제주",
            "customer": "다문화 가정 초등학생",
            "problem": "교과 어휘를 몰라 수업을 못 따라감",
            "solution": "수준 진단 후 교과 어휘 맞춤 학습",
            "revenue_model": "",
        }, ensure_ascii=False)
    ])
    messages = [
        InterviewMessage(role="assistant", content="어떤 서비스예요?"),
        InterviewMessage(role="user", content="다문화 아이들 교과 어휘 앱이요"),
    ]
    draft = await InterviewAgent(llm_provider=llm).draft_profile(MEMO, messages)
    assert draft.name == "한국어 친구"
    assert draft.location == "전국"
    assert draft.revenue_model == ""


def test_profile_route_requires_a_user_answer():
    client = TestClient(app)
    res = client.post(
        "/api/v1/interview/profile",
        json={"memo": MEMO, "messages": [{"role": "assistant", "content": "질문"}]},
    )
    assert res.status_code == 400

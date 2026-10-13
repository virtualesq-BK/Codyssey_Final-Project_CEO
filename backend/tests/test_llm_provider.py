"""
LLMProvider mock tests
"""
import pytest
from pydantic import BaseModel

from app.core.llm_provider import MockProvider


class SampleOutput(BaseModel):
    result: str
    score: float = 0.5


@pytest.mark.asyncio
async def test_mock_generate():
    provider = MockProvider(agent_name="test")
    provider.set_responses(["hello world"])
    resp = await provider.generate("test prompt")
    assert resp == "hello world"


@pytest.mark.asyncio
async def test_mock_generate_structured():
    provider = MockProvider(agent_name="test")
    provider.set_responses(['{"result": "ok", "score": 0.9}'])
    result = await provider.generate_structured("prompt", SampleOutput)
    assert result.result == "ok"
    assert result.score == 0.9


@pytest.mark.asyncio
async def test_mock_token_recording():
    provider = MockProvider(agent_name="test-agent")
    await provider.generate("prompt")
    usages = provider.get_usages()
    assert len(usages) == 1
    assert usages[0].agent_name == "test-agent"
    assert usages[0].input_tokens == 100


@pytest.mark.asyncio
async def test_mock_cycles_responses():
    provider = MockProvider()
    provider.set_responses(["a", "b"])
    r1 = await provider.generate("p")
    r2 = await provider.generate("p")
    r3 = await provider.generate("p")
    assert r1 == "a"
    assert r2 == "b"
    assert r3 == "a"


def test_parse_structured_tolerates_text_around_json():
    # 실제로 모델이 JSON 앞에 문장을 붙여 BusinessModelAgent가 3번 연속 실패했던 형태
    from pydantic import BaseModel

    from app.core.llm_provider import _parse_structured

    class Out(BaseModel):
        summary: str

    assert _parse_structured('분석 결과입니다.\n{"summary": "ok"}\n이상.', Out).summary == "ok"
    assert _parse_structured('```json\n{"summary": "fenced"}\n```', Out).summary == "fenced"
    assert _parse_structured('{"summary": "plain"}', Out).summary == "plain"

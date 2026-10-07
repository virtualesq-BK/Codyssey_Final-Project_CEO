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

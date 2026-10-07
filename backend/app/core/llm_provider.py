"""
LLMProvider abstraction
Agent가 OpenAI/Anthropic SDK를 직접 호출하지 않도록 추상화
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.core.schemas import TokenUsage

T = TypeVar("T", bound=BaseModel)

# Cost per 1K tokens (USD) – 근사치, 모델별 업데이트 필요
_COST_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "claude-3-haiku-20240307": (0.00025, 0.00125),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = _COST_TABLE.get(model, (0.001, 0.003))
    return (input_tokens / 1000 * in_rate) + (output_tokens / 1000 * out_rate)


class LLMProvider(ABC):
    """공통 LLM 인터페이스"""

    def __init__(self, model: str, agent_name: str = "unknown"):
        self.model = model
        self.agent_name = agent_name
        self._usages: list[TokenUsage] = []

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "",
    ) -> T:
        ...

    def get_usages(self) -> list[TokenUsage]:
        return list(self._usages)

    def _record(
        self,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
    ) -> TokenUsage:
        usage = TokenUsage(
            agent_name=self.agent_name,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=_estimate_cost(self.model, input_tokens, output_tokens),
        )
        self._usages.append(usage)
        return usage


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str, api_key: str, agent_name: str = "unknown"):
        super().__init__(model, agent_name)
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        t0 = time.monotonic()
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        usage = resp.usage
        self._record(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )
        return resp.choices[0].message.content or ""

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "",
    ) -> T:
        import json

        schema = response_model.model_json_schema()
        sys_msg = (system + "\n\n" if system else "") + (
            f"반드시 다음 JSON 스키마에 맞춰 응답하라:\n{json.dumps(schema, ensure_ascii=False)}"
        )
        raw = await self.generate(prompt, system=sys_msg)
        # JSON 파싱 시도
        try:
            # 코드블록 제거
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return response_model.model_validate_json(text.strip())
        except Exception:
            return response_model.model_validate_json(raw)


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str, api_key: str, agent_name: str = "unknown"):
        super().__init__(model, agent_name)
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str, system: str = "") -> str:
        t0 = time.monotonic()
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        resp = await self._client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)
        self._record(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_ms=latency_ms,
        )
        return resp.content[0].text if resp.content else ""

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "",
    ) -> T:
        import json

        schema = response_model.model_json_schema()
        sys_msg = (system + "\n\n" if system else "") + (
            f"반드시 다음 JSON 스키마에 맞춰 응답하라:\n{json.dumps(schema, ensure_ascii=False)}"
        )
        raw = await self.generate(prompt, system=sys_msg)
        try:
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return response_model.model_validate_json(text.strip())
        except Exception:
            return response_model.model_validate_json(raw)


class MockProvider(LLMProvider):
    """테스트용 Mock Provider – LLM 실제 호출 없이 동작"""

    def __init__(self, model: str = "mock", agent_name: str = "test"):
        super().__init__(model, agent_name)
        self._responses: list[str] = []
        self._index = 0

    def set_responses(self, responses: list[str]) -> None:
        self._responses = responses
        self._index = 0

    async def generate(self, prompt: str, system: str = "") -> str:
        if self._responses:
            resp = self._responses[self._index % len(self._responses)]
            self._index += 1
        else:
            resp = '{"result": "mock response"}'
        self._record(input_tokens=100, output_tokens=50, latency_ms=10)
        return resp

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "",
    ) -> T:
        raw = await self.generate(prompt, system)
        return response_model.model_validate_json(raw)


def build_provider(agent_name: str = "unknown") -> LLMProvider:
    """환경변수 기반으로 LLMProvider 인스턴스 생성"""
    from app.core.config import settings

    provider = settings.llm_provider.lower()
    model = settings.llm_model

    if provider == "anthropic":
        return AnthropicProvider(model=model, api_key=settings.anthropic_api_key, agent_name=agent_name)
    else:
        return OpenAIProvider(model=model, api_key=settings.openai_api_key, agent_name=agent_name)

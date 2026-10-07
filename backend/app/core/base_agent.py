"""
BaseAgent – 모든 Agent의 공통 인터페이스
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from app.core.llm_provider import LLMProvider, build_provider
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea, TokenUsage

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    모든 분석 Agent가 상속하는 추상 기반 클래스.
    - LLMProvider 주입 지원 (테스트 시 MockProvider 사용 가능)
    - 자동 retry / 에러 처리
    - Token usage 수집
    """

    MAX_RETRIES: int = 2
    RETRY_DELAY_SEC: float = 1.0

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        agent_name: Optional[str] = None,
    ):
        self.agent_name = agent_name or self.__class__.__name__
        self.llm = llm_provider or build_provider(self.agent_name)

    @abstractmethod
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        """실제 분석 로직 구현 – 서브클래스에서 구현"""
        ...

    async def run(self, idea: BusinessIdea) -> AgentResult:
        """retry 포함 실행 진입점"""
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES + 1):
            t0 = time.monotonic()
            try:
                logger.info("[%s] 실행 시작 (시도 %d/%d)", self.agent_name, attempt + 1, self.MAX_RETRIES + 1)
                result = await self._execute(idea)
                elapsed = int((time.monotonic() - t0) * 1000)
                result.execution_time_ms = elapsed
                logger.info("[%s] 완료 status=%s time=%dms", self.agent_name, result.status, elapsed)
                return result
            except Exception as exc:
                last_error = exc
                elapsed = int((time.monotonic() - t0) * 1000)
                logger.warning(
                    "[%s] 실패 (시도 %d) error=%s time=%dms",
                    self.agent_name,
                    attempt + 1,
                    exc,
                    elapsed,
                )
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY_SEC * (attempt + 1))

        error_msg = str(last_error) if last_error else "Unknown error"
        logger.error("[%s] 최종 실패: %s", self.agent_name, error_msg)
        return AgentResult.failed(self.agent_name, error_msg)

    def get_token_usages(self) -> list[TokenUsage]:
        return self.llm.get_usages()

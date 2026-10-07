"""
Decision Agent
모든 Agent 결과를 종합하여 최종 사업성 판단 생성
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.base_agent import BaseAgent
from app.core.llm_provider import LLMProvider
from app.core.schemas import (
    AgentResult,
    AgentStatus,
    BusinessIdea,
    Decision,
    DecisionResult,
    Evidence,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """당신은 창업 전문 컨설턴트입니다.
제공된 시장/고객/경쟁/BM/재무/리스크 분석 결과를 바탕으로
예비창업자에게 객관적인 사업성 평가를 제공합니다.

규칙:
1. 각 Agent가 제공한 Evidence 기반으로만 판단하라.
2. 근거가 없는 시장 규모나 재무 수치를 절대 생성하지 마라.
3. 근거 부족 항목은 "근거 부족 / 추가 검토 필요"로 표기하라.
4. 실제 사업 성공을 보장하는 표현을 사용하지 마라.
5. Decision은 GO / PIVOT / VALIDATE_MORE / STOP 중 하나를 선택하라.
"""


class DecisionAgent(BaseAgent):
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        agent_results: Optional[dict[str, AgentResult]] = None,
    ):
        super().__init__(llm_provider=llm_provider, agent_name="DecisionAgent")
        self._agent_results: dict[str, AgentResult] = agent_results or {}

    def set_agent_results(self, results: dict[str, AgentResult]) -> None:
        self._agent_results = results

    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        decision_result = await self._build_decision(idea)
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary=decision_result.summary,
            findings=[{"decision_result": decision_result.model_dump()}],
            evidence=decision_result.evidence,
            recommendations=decision_result.action_plan,
            confidence=decision_result.confidence,
        )

    async def decide(self, idea: BusinessIdea) -> DecisionResult:
        """Orchestrator에서 직접 호출하는 메서드"""
        return await self._build_decision(idea)

    async def _build_decision(self, idea: BusinessIdea) -> DecisionResult:
        context = self._build_context(idea)

        # LLM으로 구조화된 판단 생성
        prompt = f"""다음 사업 아이디어와 분석 결과를 검토하여 최종 판단을 내려라.

{context}

반드시 아래 JSON 형식으로만 응답하라:
{{
  "summary": "종합 요약 (2-3문장)",
  "strengths": ["강점1", "강점2"],
  "weaknesses": ["약점1", "약점2"],
  "opportunities": ["기회1", "기회2"],
  "risks": ["위험1", "위험2"],
  "financial_summary": "재무 요약 또는 '근거 부족 / 추가 검토 필요'",
  "validation_items": ["검증 필요 항목1", "검증 필요 항목2"],
  "action_plan": ["1단계: ...", "2단계: ..."],
  "decision": "GO|PIVOT|VALIDATE_MORE|STOP",
  "confidence": 0.0~1.0
}}"""

        try:
            raw = await self.llm.generate(prompt, system=_SYSTEM_PROMPT)
            parsed = self._parse_llm_response(raw)
            all_evidence = self._collect_evidence()
            parsed.evidence = all_evidence
            return parsed
        except Exception as exc:
            logger.warning("[DecisionAgent] LLM 파싱 실패, fallback 사용: %s", exc)
            return self._fallback_decision(idea)

    def _build_context(self, idea: BusinessIdea) -> str:
        lines = [
            f"## 사업 아이디어",
            f"- 제목: {idea.title}",
            f"- 문제: {idea.problem}",
            f"- 고객: {idea.customer}",
            f"- 솔루션: {idea.solution}",
            f"- 산업: {idea.industry}",
            f"- 지역: {idea.location}",
            "",
        ]

        for agent_name, result in self._agent_results.items():
            lines.append(f"## {agent_name} 결과 (신뢰도: {result.confidence:.0%})")
            lines.append(f"- 상태: {result.status}")
            lines.append(f"- 요약: {result.summary}")
            if result.findings:
                lines.append(f"- 주요 발견: {json.dumps(result.findings, ensure_ascii=False)}")
            if result.recommendations:
                lines.append(f"- 권고사항: {', '.join(result.recommendations)}")
            lines.append("")

        return "\n".join(lines)

    def _collect_evidence(self) -> list[Evidence]:
        evidence: list[Evidence] = []
        for result in self._agent_results.values():
            evidence.extend(result.evidence)
        return evidence

    def _parse_llm_response(self, raw: str) -> DecisionResult:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())

        # decision 값 정규화
        decision_str = data.get("decision", "VALIDATE_MORE").upper()
        try:
            decision = Decision(decision_str)
        except ValueError:
            decision = Decision.VALIDATE_MORE

        return DecisionResult(
            summary=data.get("summary", "분석 완료"),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            opportunities=data.get("opportunities", []),
            risks=data.get("risks", []),
            financial_summary=data.get("financial_summary", "근거 부족 / 추가 검토 필요"),
            validation_items=data.get("validation_items", []),
            action_plan=data.get("action_plan", []),
            decision=decision,
            confidence=float(data.get("confidence", 0.5)),
        )

    def _fallback_decision(self, idea: BusinessIdea) -> DecisionResult:
        """LLM 실패 시 기본 구조 반환"""
        available = [
            name for name, r in self._agent_results.items()
            if r.status == AgentStatus.SUCCESS
        ]
        failed = [
            name for name, r in self._agent_results.items()
            if r.status == AgentStatus.FAILED
        ]

        return DecisionResult(
            summary=(
                f"'{idea.title}' 사업 아이디어 분석이 부분적으로 완료되었습니다. "
                f"완료된 분석: {', '.join(available) or '없음'}. "
                f"추가 검토 필요."
            ),
            strengths=["사업 아이디어 구체성 확인 필요"],
            weaknesses=["일부 분석 결과 미수집" if failed else "분석 데이터 부족"],
            opportunities=["추가 검증을 통한 기회 발굴 가능"],
            risks=["현재 정보로는 리스크 정량화 불가"],
            financial_summary="근거 부족 / 추가 검토 필요",
            validation_items=[
                "고객 인터뷰 최소 10건",
                "경쟁사 상세 분석",
                "초기 비용 구조 확인",
            ],
            action_plan=[
                "1단계: 핵심 가정 목록 작성",
                "2단계: 고객 인터뷰로 가정 검증",
                "3단계: 소규모 파일럿 실행",
            ],
            decision=Decision.VALIDATE_MORE,
            confidence=0.3,
        )

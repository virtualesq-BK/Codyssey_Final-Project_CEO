"""
재무 시나리오 계산 API (보고서 화면에서 사용자가 숫자를 넣으면 바로 계산)
계산은 D팀의 결정적 계산기(app.financial.calculator)를 그대로 쓴다 — LLM 없이 Python 계산.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.financial.calculator import FinancialInputs, ScenarioResult, run_scenarios

router = APIRouter(prefix="/api/v1/finance")

# 사용자가 직접 넣은 숫자 — financial_agent의 USER_INPUT_CONFIDENCE와 맞춘다
USER_INPUT_CONFIDENCE = 0.75


class ScenarioRequest(BaseModel):
    inputs: FinancialInputs


class ScenarioResponse(BaseModel):
    scenarios: list[ScenarioResult]


@router.post("/scenarios", response_model=ScenarioResponse)
async def scenarios(req: ScenarioRequest) -> ScenarioResponse:
    return ScenarioResponse(scenarios=run_scenarios(req.inputs, USER_INPUT_CONFIDENCE))

"""
딥 인터뷰 · 1차 분석 API
기존 routes.py(분석·공고)와 분리해 둔다.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.interview_agent import (
    Coverage,
    InterviewAgent,
    InterviewMessage,
    InterviewTurn,
    ProfileDraft,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interview")


class InterviewRequest(BaseModel):
    memo: str = Field(min_length=1, max_length=2000)
    messages: list[InterviewMessage] = Field(default_factory=list, max_length=40)
    covered: Optional[Coverage] = None


@router.post("/next", response_model=InterviewTurn)
async def next_question(req: InterviewRequest) -> InterviewTurn:
    try:
        return await InterviewAgent().next_turn(req.memo, req.messages, req.covered)
    except Exception as exc:
        logger.error("[interview/next] 실패: %s", exc)
        raise HTTPException(status_code=502, detail=f"인터뷰 질문을 만들지 못했어요: {exc}")


@router.post("/profile", response_model=ProfileDraft)
async def draft_profile(req: InterviewRequest) -> ProfileDraft:
    if not any(m.role == "user" for m in req.messages):
        raise HTTPException(status_code=400, detail="인터뷰 답변이 하나도 없어요.")
    try:
        return await InterviewAgent().draft_profile(req.memo, req.messages)
    except Exception as exc:
        logger.error("[interview/profile] 실패: %s", exc)
        raise HTTPException(status_code=502, detail=f"프로필 초안을 만들지 못했어요: {exc}")

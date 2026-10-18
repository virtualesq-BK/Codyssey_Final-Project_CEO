"""
딥 인터뷰 · 1차 분석 API
기존 routes.py(분석·공고)와 분리해 둔다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
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


# ── 비로그인 '프로필 미리보기' — 메모 한 줄로 프로필 1~3 초안을 만든다 (같은 IP 하루 1회) ──

KST = timezone(timedelta(hours=9))
# 서버 메모리에만 둔다 (재시작하면 초기화 — 비용 남용을 막는 정도의 가벼운 제한)
_preview_used: dict[str, str] = {}


class PreviewRequest(BaseModel):
    memo: str = Field(min_length=1, max_length=2000)


def client_ip(request: Request) -> str:
    # Next 프록시·Tailscale·Render를 거치면 실제 주소는 X-Forwarded-For 맨 앞에 있다
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/preview-profile", response_model=ProfileDraft)
async def preview_profile(req: PreviewRequest, request: Request) -> ProfileDraft:
    ip = client_ip(request)
    today = datetime.now(KST).date().isoformat()
    if _preview_used.get(ip) == today:
        raise HTTPException(status_code=429, detail="오늘은 프로필 미리보기를 이미 사용했어요. 로그인하면 AI 인터뷰로 제대로 만들 수 있어요.")
    # 생성이 실패하면 횟수를 쓰지 않도록, 성공한 뒤에 기록한다
    try:
        draft = await InterviewAgent().draft_profile(req.memo, [])
    except Exception as exc:
        logger.error("[interview/preview-profile] 실패: %s", exc)
        raise HTTPException(status_code=502, detail="프로필 미리보기를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.")
    if len(_preview_used) > 50_000:
        _preview_used.clear()
    _preview_used[ip] = today
    return draft
